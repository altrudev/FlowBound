from __future__ import annotations

from dataclasses import dataclass

POLICY_VERSION = "2026-08-26.demo-v1"


@dataclass(frozen=True)
class EffectRule:
    effect: str
    predecessors: frozenset[str]
    successor_state: str
    required_authority: str
    requires_human_approval: bool = False


_RULES: dict[str, EffectRule] = {
    "CREATE_REMEDIATION_TASK": EffectRule(
        effect="CREATE_REMEDIATION_TASK",
        predecessors=frozenset({"OPEN"}),
        successor_state="REMEDIATION_PENDING",
        required_authority="remediation:create",
    ),
    "SCHEDULE_FOLLOW_UP": EffectRule(
        effect="SCHEDULE_FOLLOW_UP",
        predecessors=frozenset({"REMEDIATION_PENDING"}),
        successor_state="FOLLOW_UP_SCHEDULED",
        required_authority="followup:schedule",
    ),
    "CLOSE_CASE": EffectRule(
        effect="CLOSE_CASE",
        predecessors=frozenset({"FOLLOW_UP_VERIFIED"}),
        successor_state="CLOSED",
        required_authority="case:close",
        requires_human_approval=True,
    ),
}


def resolve_effect(effect: str) -> EffectRule | None:
    return _RULES.get(effect)


def permitted_effects(state: str, authorities: frozenset[str]) -> frozenset[str]:
    return frozenset(
        rule.effect
        for rule in _RULES.values()
        if state in rule.predecessors and rule.required_authority in authorities
    )
