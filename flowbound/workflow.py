from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from .gate import Decision, GateResult, TransitionProposal, evaluate_transition
from .policy import EffectRule, POLICY_VERSION, permitted_effects, resolve_effect
from .state import StateConflict, StateSnapshot


class DecisionStore(Protocol):
    def record_decision(self, **payload: Any) -> None: ...


class GovernedStore(DecisionStore, Protocol):
    def get_case_snapshot(self, case_id: str) -> StateSnapshot: ...
    def compare_and_set_case_state(
        self, *, case_id: str, expected: StateSnapshot, successor_state: str, transition_id: str
    ) -> StateSnapshot: ...
    def record_execution(self, **payload: Any) -> None: ...
    def record_verification(self, **payload: Any) -> None: ...
    def is_recovery_required(self, case_id: str) -> bool: ...
    def set_recovery_required(self, *, case_id: str, transition_id: str, reason: str) -> None: ...


class EventPublisher(Protocol):
    def publish(self, event_type: str, payload: dict[str, Any]) -> str: ...


class VerificationStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_RUN = "NOT_RUN"


@dataclass(frozen=True)
class ExecutionReceipt:
    applied: bool
    executor: str
    transition_id: str
    reason: str


@dataclass(frozen=True)
class SuccessorVerification:
    status: VerificationStatus
    expected_state: str
    expected_revision: int
    observed_state: str
    observed_revision: int
    reason: str


@dataclass(frozen=True)
class TransitionOutcome:
    gate: GateResult
    execution: ExecutionReceipt | None
    verification: SuccessorVerification | None
    event_ids: tuple[str, ...]


class CaseStateExecutor:
    """Executes only a policy-derived state effect using optimistic CAS."""

    def __init__(self, store: GovernedStore) -> None:
        self._store = store

    def execute(
        self,
        *,
        case_id: str,
        transition_id: str,
        predecessor: StateSnapshot,
        rule: EffectRule,
    ) -> ExecutionReceipt:
        try:
            self._store.compare_and_set_case_state(
                case_id=case_id,
                expected=predecessor,
                successor_state=rule.successor_state,
                transition_id=transition_id,
            )
        except StateConflict as exc:
            return ExecutionReceipt(False, "case-state-cas", transition_id, str(exc))
        return ExecutionReceipt(True, "case-state-cas", transition_id, "Effect applied")


class StoreStateObserver:
    """Reads observed state independently of the executor receipt."""

    def __init__(self, store: GovernedStore) -> None:
        self._store = store

    def observe(self, case_id: str) -> StateSnapshot:
        return self._store.get_case_snapshot(case_id)


def verify_successor(
    *,
    predecessor: StateSnapshot,
    rule: EffectRule,
    observed: StateSnapshot,
) -> SuccessorVerification:
    expected_revision = predecessor.revision + 1
    ok = observed.state == rule.successor_state and observed.revision == expected_revision
    if ok:
        return SuccessorVerification(
            VerificationStatus.PASS,
            rule.successor_state,
            expected_revision,
            observed.state,
            observed.revision,
            "Observed successor exactly matches the authorized state and revision.",
        )
    return SuccessorVerification(
        VerificationStatus.FAIL,
        rule.successor_state,
        expected_revision,
        observed.state,
        observed.revision,
        "Observed successor differs from the authorized effect or expected revision.",
    )


def process_transition(
    *,
    case_id: str,
    transition_id: str,
    proposal: TransitionProposal,
    store: DecisionStore,
    events: EventPublisher,
) -> GateResult:
    """Backward-compatible evaluate/persist/publish path."""
    result = evaluate_transition(proposal)
    store.record_decision(case_id=case_id, transition_id=transition_id, proposal=proposal, result=result)
    events.publish(
        "flowbound.transition.decided",
        {"case_id": case_id, "transition_id": transition_id, "decision": result.decision.value},
    )
    return result


def govern_and_execute(
    *,
    case_id: str,
    transition_id: str,
    actor: str,
    actor_authorities: frozenset[str],
    authorized_predecessor: StateSnapshot,
    requested_effect: str,
    evidence_trusted: bool,
    human_approval_present: bool,
    store: GovernedStore,
    events: EventPublisher,
    executor: CaseStateExecutor | None = None,
    observer: StoreStateObserver | None = None,
    evidence_ids: tuple[str, ...] = (),
    originating_need: str = "",
    agent_rationale: str = "",
) -> TransitionOutcome:
    """Authorize, execute, then independently re-observe and verify one transition."""
    executor = executor or CaseStateExecutor(store)
    observer = observer or StoreStateObserver(store)
    current = observer.observe(case_id)
    rule = resolve_effect(requested_effect)

    if rule is None:
        proposal = TransitionProposal(
            actor=actor,
            predecessor_state=authorized_predecessor.token,
            observed_state=current.token,
            requested_effect=requested_effect,
            allowed_effects=frozenset(),
            actor_authorities=actor_authorities,
            required_authority="undefined-effect",
            evidence_trusted=evidence_trusted,
            human_approval_present=human_approval_present,
            policy_version=POLICY_VERSION,
            evidence_ids=evidence_ids,
            originating_need=originating_need,
            agent_rationale=agent_rationale,
        )
    else:
        proposal = TransitionProposal(
            actor=actor,
            predecessor_state=authorized_predecessor.token,
            observed_state=current.token,
            requested_effect=requested_effect,
            allowed_effects=permitted_effects(current.state, actor_authorities),
            actor_authorities=actor_authorities,
            required_authority=rule.required_authority,
            evidence_trusted=evidence_trusted,
            requires_human_approval=rule.requires_human_approval,
            human_approval_present=human_approval_present,
            policy_version=POLICY_VERSION,
            evidence_ids=evidence_ids,
            originating_need=originating_need,
            agent_rationale=agent_rationale,
        )

    gate = evaluate_transition(proposal)
    store.record_decision(case_id=case_id, transition_id=transition_id, proposal=proposal, result=gate)
    event_ids = [events.publish(
        "flowbound.transition.decided",
        {"case_id": case_id, "transition_id": transition_id, "decision": gate.decision.value},
    )]

    if gate.decision is not Decision.ALLOW or rule is None:
        return TransitionOutcome(gate, None, None, tuple(event_ids))

    receipt = executor.execute(
        case_id=case_id,
        transition_id=transition_id,
        predecessor=current,
        rule=rule,
    )
    store.record_execution(case_id=case_id, transition_id=transition_id, receipt=receipt)
    event_ids.append(events.publish(
        "flowbound.transition.executed",
        {"case_id": case_id, "transition_id": transition_id, "applied": str(receipt.applied).lower()},
    ))

    observed = observer.observe(case_id)
    verification = verify_successor(predecessor=current, rule=rule, observed=observed)
    store.record_verification(case_id=case_id, transition_id=transition_id, verification=verification)
    event_ids.append(events.publish(
        "flowbound.transition.verified",
        {"case_id": case_id, "transition_id": transition_id, "status": verification.status.value},
    ))

    if verification.status is VerificationStatus.PASS:
        event_ids.append(events.publish(
            "flowbound.transition.accepted",
            {"case_id": case_id, "transition_id": transition_id},
        ))
    else:
        store.set_recovery_required(
            case_id=case_id,
            transition_id=transition_id,
            reason=verification.reason,
        )
        event_ids.append(events.publish(
            "flowbound.transition.recovery_required",
            {"case_id": case_id, "transition_id": transition_id, "reason": verification.reason},
        ))

    return TransitionOutcome(gate, receipt, verification, tuple(event_ids))
