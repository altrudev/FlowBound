from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StateSnapshot:
    state: str
    revision: int

    @property
    def token(self) -> str:
        return f"{self.state}@{self.revision}"


class StateConflict(RuntimeError):
    pass


class InMemoryCaseStore:
    """Deterministic local/test state store with compare-and-set semantics."""

    def __init__(self) -> None:
        self.cases: dict[str, StateSnapshot] = {}
        self.decisions: dict[tuple[str, str], dict[str, Any]] = {}
        self.executions: dict[tuple[str, str], dict[str, Any]] = {}
        self.verifications: dict[tuple[str, str], dict[str, Any]] = {}

    def create_case(self, case_id: str, state: str = "OPEN") -> StateSnapshot:
        if case_id in self.cases:
            raise ValueError(f"Case already exists: {case_id}")
        snapshot = StateSnapshot(state=state, revision=0)
        self.cases[case_id] = snapshot
        return snapshot

    def get_case_snapshot(self, case_id: str) -> StateSnapshot:
        try:
            return self.cases[case_id]
        except KeyError as exc:
            raise KeyError(f"Unknown case: {case_id}") from exc

    def compare_and_set_case_state(
        self,
        *,
        case_id: str,
        expected: StateSnapshot,
        successor_state: str,
        transition_id: str,
    ) -> StateSnapshot:
        current = self.get_case_snapshot(case_id)
        if current != expected:
            raise StateConflict(
                f"State changed before execution: expected {expected.token}, got {current.token}"
            )
        successor = StateSnapshot(successor_state, current.revision + 1)
        self.cases[case_id] = successor
        return successor

    def record_decision(self, **payload: Any) -> None:
        self.decisions[(payload["case_id"], payload["transition_id"])] = payload

    def record_execution(self, **payload: Any) -> None:
        self.executions[(payload["case_id"], payload["transition_id"])] = payload

    def record_verification(self, **payload: Any) -> None:
        self.verifications[(payload["case_id"], payload["transition_id"])] = payload
