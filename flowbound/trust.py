from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EvidenceAssessment:
    trusted: bool
    source: str
    reason: str
    signals: tuple[str, ...] = ()


class EvidenceAssessor(Protocol):
    def assess(self, *, observation: str, evidence_ids: tuple[str, ...] = ()) -> EvidenceAssessment: ...


class RuleBasedEvidenceAssessor:
    """Credential-free pre-model trust boundary for local/demo execution.

    This does not claim to be a full prompt-injection detector. It prevents callers
    from self-asserting trust and fails closed on obvious instruction-like content
    before any model sees the evidence.
    """

    _PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
        ("instruction_override", re.compile(r"\b(ignore|disregard|override)\b.{0,48}\b(instruction|policy|rule|system|previous)\b", re.IGNORECASE | re.DOTALL)),
        ("role_impersonation", re.compile(r"\b(system|developer|assistant)\s*(message|prompt|instruction)\b", re.IGNORECASE)),
        ("secret_exfiltration", re.compile(r"\b(reveal|print|send|exfiltrate|leak)\b.{0,64}\b(secret|token|credential|password|api[_ -]?key)\b", re.IGNORECASE | re.DOTALL)),
        ("tool_directive", re.compile(r"\b(call|invoke|execute|run)\b.{0,48}\b(tool|shell|command|function|api)\b", re.IGNORECASE | re.DOTALL)),
    )

    def assess(self, *, observation: str, evidence_ids: tuple[str, ...] = ()) -> EvidenceAssessment:
        signals = tuple(name for name, pattern in self._PATTERNS if pattern.search(observation))
        if signals:
            return EvidenceAssessment(
                trusted=False,
                source="flowbound.rule-preflight.v1",
                reason="Instruction-like or exfiltration-like content detected before model execution.",
                signals=signals,
            )
        return EvidenceAssessment(
            trusted=True,
            source="flowbound.rule-preflight.v1",
            reason="No configured pre-model quarantine signal matched.",
            signals=(),
        )
