from __future__ import annotations

from typing import Protocol

from .gate import GateResult, TransitionProposal, evaluate_transition


class DecisionStore(Protocol):
    def record_decision(
        self,
        *,
        case_id: str,
        transition_id: str,
        proposal: TransitionProposal,
        result: GateResult,
    ) -> None: ...


class EventPublisher(Protocol):
    def publish(self, event_type: str, payload: dict[str, str]) -> str: ...


def process_transition(
    *,
    case_id: str,
    transition_id: str,
    proposal: TransitionProposal,
    store: DecisionStore,
    events: EventPublisher,
) -> GateResult:
    """Evaluate, persist, and emit the outcome of one proposed transition."""

    result = evaluate_transition(proposal)
    store.record_decision(
        case_id=case_id,
        transition_id=transition_id,
        proposal=proposal,
        result=result,
    )
    events.publish(
        "flowbound.transition.decided",
        {
            "case_id": case_id,
            "transition_id": transition_id,
            "decision": result.decision.value,
        },
    )
    return result
