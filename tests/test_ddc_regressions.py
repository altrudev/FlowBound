from flowbound.events import InMemoryEventPublisher
from flowbound.gate import Decision
from flowbound.state import InMemoryCaseStore
from flowbound.workflow import govern_and_execute


def test_untrusted_evidence_quarantines_without_execution():
    store = InMemoryCaseStore(); events = InMemoryEventPublisher(); predecessor = store.create_case("q1")
    outcome = govern_and_execute(
        case_id="q1", transition_id="tx-q", actor="agent",
        actor_authorities=frozenset({"remediation:create"}), authorized_predecessor=predecessor,
        requested_effect="CREATE_REMEDIATION_TASK", evidence_trusted=False,
        human_approval_present=False, store=store, events=events,
    )
    assert outcome.gate.decision is Decision.QUARANTINE
    assert outcome.execution is None
    assert store.get_case_snapshot("q1") == predecessor


def test_successful_transition_emits_decide_execute_verify_lineage():
    store = InMemoryCaseStore(); events = InMemoryEventPublisher(); predecessor = store.create_case("e1")
    govern_and_execute(
        case_id="e1", transition_id="tx-e", actor="agent",
        actor_authorities=frozenset({"remediation:create"}), authorized_predecessor=predecessor,
        requested_effect="CREATE_REMEDIATION_TASK", evidence_trusted=True,
        human_approval_present=False, store=store, events=events,
    )
    assert [event["event_type"] for event in events.events] == [
        "flowbound.transition.decided",
        "flowbound.transition.executed",
        "flowbound.transition.verified",
    ]
