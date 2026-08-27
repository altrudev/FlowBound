import asyncio

from flowbound.events import InMemoryEventPublisher
from flowbound.gate import Decision, TransitionProposal, evaluate_transition
from flowbound.service import AgentActionProposal, FlowBoundService
from flowbound.state import InMemoryCaseStore, StateConflict, StateSnapshot
from flowbound.workflow import (
    CaseStateExecutor,
    ExecutionReceipt,
    StoreStateObserver,
    VerificationStatus,
    govern_and_execute,
)


def proposal(**overrides):
    base = dict(
        actor="inspection-action-agent",
        predecessor_state="OPEN@0",
        observed_state="OPEN@0",
        requested_effect="CREATE_REMEDIATION_TASK",
        allowed_effects=frozenset({"CREATE_REMEDIATION_TASK"}),
        actor_authorities=frozenset({"remediation:create"}),
        required_authority="remediation:create",
    )
    base.update(overrides)
    return TransitionProposal(**base)


def test_gate_allows_revision_bound_transition():
    assert evaluate_transition(proposal()).decision is Decision.ALLOW


def test_gate_rejects_stale_revision_even_same_state_label():
    assert evaluate_transition(proposal(observed_state="OPEN@1")).decision is Decision.REJECT


def test_memory_store_compare_and_set_blocks_stale_execution():
    store = InMemoryCaseStore()
    old = store.create_case("c1")
    store.compare_and_set_case_state(case_id="c1", expected=old, successor_state="REMEDIATION_PENDING", transition_id="other")
    try:
        store.compare_and_set_case_state(case_id="c1", expected=old, successor_state="CLOSED", transition_id="tx")
    except StateConflict:
        pass
    else:
        raise AssertionError("expected stale-state conflict")


def test_end_to_end_allow_execute_verify():
    store = InMemoryCaseStore(); events = InMemoryEventPublisher(); predecessor = store.create_case("case-1")
    outcome = govern_and_execute(
        case_id="case-1", transition_id="tx-1", actor="flowbound_action_agent",
        actor_authorities=frozenset({"remediation:create"}), authorized_predecessor=predecessor,
        requested_effect="CREATE_REMEDIATION_TASK", evidence_trusted=True, human_approval_present=False,
        store=store, events=events,
    )
    assert outcome.gate.decision is Decision.ALLOW
    assert outcome.execution and outcome.execution.applied
    assert outcome.verification and outcome.verification.status is VerificationStatus.PASS
    assert store.get_case_snapshot("case-1") == StateSnapshot("REMEDIATION_PENDING", 1)


def test_stale_predecessor_blocks_before_execution():
    store = InMemoryCaseStore(); events = InMemoryEventPublisher(); predecessor = store.create_case("case-1")
    store.compare_and_set_case_state(case_id="case-1", expected=predecessor, successor_state="REMEDIATION_PENDING", transition_id="other")
    outcome = govern_and_execute(
        case_id="case-1", transition_id="tx-stale", actor="flowbound_action_agent",
        actor_authorities=frozenset({"remediation:create"}), authorized_predecessor=predecessor,
        requested_effect="CREATE_REMEDIATION_TASK", evidence_trusted=True, human_approval_present=False,
        store=store, events=events,
    )
    assert outcome.gate.decision is Decision.REJECT
    assert outcome.execution is None


def test_wrong_authority_and_unknown_effect_are_rejected():
    store = InMemoryCaseStore(); events = InMemoryEventPublisher(); predecessor = store.create_case("c")
    wrong = govern_and_execute(
        case_id="c", transition_id="tx1", actor="agent", actor_authorities=frozenset({"followup:schedule"}),
        authorized_predecessor=predecessor, requested_effect="CREATE_REMEDIATION_TASK",
        evidence_trusted=True, human_approval_present=False, store=store, events=events,
    )
    assert wrong.gate.decision is Decision.REJECT
    unknown = govern_and_execute(
        case_id="c", transition_id="tx2", actor="agent", actor_authorities=frozenset({"building:destroy"}),
        authorized_predecessor=predecessor, requested_effect="DEMOLISH_BUILDING",
        evidence_trusted=True, human_approval_present=False, store=store, events=events,
    )
    assert unknown.gate.decision is Decision.REJECT


def test_close_case_requires_human_approval():
    store = InMemoryCaseStore(); events = InMemoryEventPublisher(); store.cases["c"] = StateSnapshot("FOLLOW_UP_VERIFIED", 4)
    out = govern_and_execute(
        case_id="c", transition_id="tx", actor="agent", actor_authorities=frozenset({"case:close"}),
        authorized_predecessor=store.get_case_snapshot("c"), requested_effect="CLOSE_CASE",
        evidence_trusted=True, human_approval_present=False, store=store, events=events,
    )
    assert out.gate.decision is Decision.ESCALATE


class LyingExecutor(CaseStateExecutor):
    def execute(self, **kwargs):
        return ExecutionReceipt(True, "lying-executor", kwargs["transition_id"], "claimed success")


def test_verifier_does_not_trust_executor_receipt():
    store = InMemoryCaseStore(); events = InMemoryEventPublisher(); predecessor = store.create_case("c")
    out = govern_and_execute(
        case_id="c", transition_id="tx", actor="agent", actor_authorities=frozenset({"remediation:create"}),
        authorized_predecessor=predecessor, requested_effect="CREATE_REMEDIATION_TASK",
        evidence_trusted=True, human_approval_present=False, store=store, events=events,
        executor=LyingExecutor(store), observer=StoreStateObserver(store),
    )
    assert out.execution and out.execution.applied
    assert out.verification and out.verification.status is VerificationStatus.FAIL
    assert store.get_case_snapshot("c") == StateSnapshot("OPEN", 0)


class FakeGoogleAgent:
    async def propose(self, *, observation: str, predecessor_state: str):
        assert predecessor_state == "OPEN"
        return AgentActionProposal("CREATE_REMEDIATION_TASK", "defect requires remediation")


def test_service_connects_agent_to_governed_execution():
    store = InMemoryCaseStore(); store.create_case("c1")
    service = FlowBoundService(
        agent=FakeGoogleAgent(), store=store, events=InMemoryEventPublisher(), actor="flowbound_action_agent",
        actor_authorities=frozenset({"remediation:create"}),
    )
    _, outcome = asyncio.run(service.run_case(
        case_id="c1", transition_id="tx1", observation="door will not latch",
        evidence_trusted=True, human_approval_present=False,
    ))
    assert outcome.verification and outcome.verification.status is VerificationStatus.PASS


class RacingAgent:
    def __init__(self, store): self.store = store
    async def propose(self, *, observation: str, predecessor_state: str):
        old = self.store.get_case_snapshot("c1")
        self.store.compare_and_set_case_state(case_id="c1", expected=old, successor_state="REMEDIATION_PENDING", transition_id="race")
        return AgentActionProposal("CREATE_REMEDIATION_TASK", "stale proposal")


def test_state_change_during_model_reasoning_is_rejected():
    store = InMemoryCaseStore(); store.create_case("c1")
    service = FlowBoundService(
        agent=RacingAgent(store), store=store, events=InMemoryEventPublisher(), actor="flowbound_action_agent",
        actor_authorities=frozenset({"remediation:create"}),
    )
    _, outcome = asyncio.run(service.run_case(
        case_id="c1", transition_id="tx1", observation="door will not latch",
        evidence_trusted=True, human_approval_present=False,
    ))
    assert outcome.gate.decision is Decision.REJECT
    assert outcome.execution is None
