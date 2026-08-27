from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .gate import GateResult, TransitionProposal
from .state import StateConflict, StateSnapshot


def _firestore_safe(value: Any) -> Any:
    if isinstance(value, frozenset):
        return sorted(value)
    if isinstance(value, tuple):
        return [_firestore_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _firestore_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_firestore_safe(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return _firestore_safe(asdict(value))
    return value


class FirestoreTransitionStore:
    """Durable FlowBound case state and transition evidence in Cloud Firestore."""

    def __init__(self, project: str | None = None, database: str | None = None, client: Any | None = None) -> None:
        if client is None:
            from google.cloud import firestore
            client = firestore.Client(project=project, database=database)
        self._client = client

    def create_case(self, case_id: str, state: str = "OPEN") -> StateSnapshot:
        snapshot = StateSnapshot(state=state, revision=0)
        self._client.collection("cases").document(case_id).set(
            {"state": snapshot.state, "revision": snapshot.revision, "recovery_required": False}
        )
        return snapshot

    def get_case_snapshot(self, case_id: str) -> StateSnapshot:
        doc = self._client.collection("cases").document(case_id).get()
        if not getattr(doc, "exists", True):
            raise KeyError(f"Unknown case: {case_id}")
        data = doc.to_dict() or {}
        if "state" not in data or "revision" not in data:
            raise KeyError(f"Case has no valid state snapshot: {case_id}")
        return StateSnapshot(state=str(data["state"]), revision=int(data["revision"]))

    def compare_and_set_case_state(
        self,
        *,
        case_id: str,
        expected: StateSnapshot,
        successor_state: str,
        transition_id: str,
    ) -> StateSnapshot:
        """Atomically mutate the case only if the exact predecessor revision is current."""
        from google.cloud import firestore

        doc_ref = self._client.collection("cases").document(case_id)
        transaction = self._client.transaction()

        @firestore.transactional
        def mutate(txn):
            doc = doc_ref.get(transaction=txn)
            if not doc.exists:
                raise KeyError(f"Unknown case: {case_id}")
            data = doc.to_dict() or {}
            current = StateSnapshot(str(data.get("state")), int(data.get("revision", -1)))
            if current != expected:
                raise StateConflict(
                    f"State changed before execution: expected {expected.token}, got {current.token}"
                )
            successor = StateSnapshot(successor_state, current.revision + 1)
            txn.set(
                doc_ref,
                {
                    "state": successor.state,
                    "revision": successor.revision,
                    "last_transition_id": transition_id,
                },
                merge=True,
            )
            return successor

        return mutate(transaction)

    def is_recovery_required(self, case_id: str) -> bool:
        doc = self._client.collection("cases").document(case_id).get()
        if not getattr(doc, "exists", True):
            raise KeyError(f"Unknown case: {case_id}")
        return bool((doc.to_dict() or {}).get("recovery_required", False))

    def set_recovery_required(self, *, case_id: str, transition_id: str, reason: str) -> None:
        self._client.collection("cases").document(case_id).set(
            {
                "recovery_required": True,
                "recovery_transition_id": transition_id,
                "recovery_reason": reason,
            },
            merge=True,
        )

    def record_decision(self, *, case_id: str, transition_id: str, proposal: TransitionProposal, result: GateResult) -> None:
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

    def record_execution(self, *, case_id: str, transition_id: str, receipt: Any) -> None:
        (
            self._client.collection("cases")
            .document(case_id)
            .collection("executions")
            .document(transition_id)
            .set(_firestore_safe(receipt))
        )

    def record_verification(self, *, case_id: str, transition_id: str, verification: Any) -> None:
        (
            self._client.collection("cases")
            .document(case_id)
            .collection("verifications")
            .document(transition_id)
            .set(_firestore_safe(verification))
        )
