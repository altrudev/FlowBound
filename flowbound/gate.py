from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Decision(StrEnum):
    ALLOW = "ALLOW"
    REJECT = "REJECT"
    ESCALATE = "ESCALATE"
    QUARANTINE = "QUARANTINE"


@dataclass(frozen=True)
class TransitionProposal:
    actor: str
    predecessor_state: str
    observed_state: str
    requested_effect: str
    allowed_effects: frozenset[str]
    actor_authorities: frozenset[str]
    required_authority: str
    evidence_trusted: bool = True
    requires_human_approval: bool = False
    human_approval_present: bool = False
    policy_version: str = "unknown"
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class GateResult:
    decision: Decision
    reason: str


def evaluate_transition(proposal: TransitionProposal) -> GateResult:
    """Evaluate a proposed consequential transition without model judgment."""
    if not proposal.evidence_trusted:
        return GateResult(
            Decision.QUARANTINE,
            "Evidence or input is marked untrusted and cannot authorize execution.",
        )

    if proposal.predecessor_state != proposal.observed_state:
        return GateResult(
            Decision.REJECT,
            "Predecessor state is stale; authorization must be recomputed.",
        )

    if proposal.required_authority not in proposal.actor_authorities:
        return GateResult(
            Decision.REJECT,
            "Actor does not possess the authority required for this transition.",
        )

    if proposal.requested_effect not in proposal.allowed_effects:
        return GateResult(
            Decision.REJECT,
            "Requested effect falls outside the authorized effect envelope.",
        )

    if proposal.requires_human_approval and not proposal.human_approval_present:
        return GateResult(
            Decision.ESCALATE,
            "Transition is otherwise valid but requires explicit human approval.",
        )

    return GateResult(
        Decision.ALLOW,
        "Transition is inside the current authority and effect envelope.",
    )
