from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .gate import GateResult, TransitionProposal


def _firestore_safe(value: Any) -> Any:
    if isinstance(value, frozenset):
        return sorted(value)
    if isinstance(value, dict):
        return {key: _firestore_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_firestore_safe(item) for item in value]
    return value


class FirestoreTransitionStore:
    """Persist FlowBound transition decisions to Cloud Firestore."""

    def __init__(
        self,
        project: str | None = None,
        database: str | None = None,
        client: Any | None = None,
    ) -> None:
        if client is None:
            from google.cloud import firestore

            client = firestore.Client(project=project, database=database)
        self._client = client

    def record_decision(
        self,
        *,
        case_id: str,
        transition_id: str,
        proposal: TransitionProposal,
        result: GateResult,
    ) -> None:
        payload = {
            "proposal": _firestore_safe(asdict(proposal)),
            "decision": result.decision.value,
            "reason": result.reason,
        }
        (
            self._client.collection("cases")
            .document(case_id)
            .collection("transitions")
            .document(transition_id)
            .set(payload)
        )
