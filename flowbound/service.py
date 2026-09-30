from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .trust import EvidenceAssessment, EvidenceAssessor, RuleBasedEvidenceAssessor
from .workflow import EventPublisher, GovernedStore, TransitionOutcome, govern_and_execute


@dataclass(frozen=True)
class AgentActionProposal:
    requested_effect: str
    rationale: str


@dataclass(frozen=True)
class RecoveryResult:
    cleared: bool
    reason: str
    evidence_ids: tuple[str, ...]


class ProposalAgent(Protocol):
    async def propose(self, *, observation: str, predecessor_state: str) -> AgentActionProposal: ...


class DeterministicDemoAgent:
    """Credential-free local fallback. The competition path uses Google ADK/Gemini."""

    async def propose(self, *, observation: str, predecessor_state: str) -> AgentActionProposal:
        if predecessor_state == "OPEN":
            effect = "CREATE_REMEDIATION_TASK"
        elif predecessor_state == "REMEDIATION_PENDING":
            effect = "SCHEDULE_FOLLOW_UP"
        else:
            effect = "CLOSE_CASE"
        return AgentActionProposal(effect, "Deterministic development fallback")


class FlowBoundService:
    def __init__(
        self,
        *,
        agent: ProposalAgent,
        store: GovernedStore,
        events: EventPublisher,
        actor: str,
        actor_authorities: frozenset[str],
        evidence_assessor: EvidenceAssessor | None = None,
    ) -> None:
        self.agent = agent
        self.store = store
        self.events = events
        self.actor = actor
        self.actor_authorities = actor_authorities
        self.evidence_assessor = evidence_assessor or RuleBasedEvidenceAssessor()

    async def run_case(
        self,
        *,
        case_id: str,
        transition_id: str,
        observation: str,
        human_approval_present: bool,
        evidence_ids: tuple[str, ...] = (),
        evidence_trusted: bool | None = None,
        include_assessment: bool = False,
    ):
        if self.store.is_recovery_required(case_id):
            raise RuntimeError(f"Case {case_id} is blocked pending independent recovery evidence")

        authorized_predecessor = self.store.get_case_snapshot(case_id)
        assessment = self.evidence_assessor.assess(observation=observation, evidence_ids=evidence_ids)
        if evidence_trusted is not None:
            # Internal/test override only. The public API never accepts caller asserted trust.
            assessment = EvidenceAssessment(
                trusted=evidence_trusted,
                source="internal-test-override",
                reason="Explicit internal test override.",
            )

        if not assessment.trusted:
            agent_proposal = AgentActionProposal(
                requested_effect="NO_ACTION",
                rationale="Evidence quarantined before model execution.",
            )
        else:
            agent_proposal = await self.agent.propose(
                observation=observation,
                predecessor_state=authorized_predecessor.state,
            )

        outcome = govern_and_execute(
            case_id=case_id,
            transition_id=transition_id,
            actor=self.actor,
            actor_authorities=self.actor_authorities,
            authorized_predecessor=authorized_predecessor,
            requested_effect=agent_proposal.requested_effect,
            evidence_trusted=assessment.trusted,
            evidence_trust_source=assessment.source,
            evidence_trust_reason=assessment.reason,
            human_approval_present=human_approval_present,
            store=self.store,
            events=self.events,
            evidence_ids=evidence_ids,
            originating_need=observation,
            agent_rationale=agent_proposal.rationale,
        )
        if include_assessment:
            return agent_proposal, outcome, assessment
        return agent_proposal, outcome

    def recover_case(
        self,
        *,
        case_id: str,
        recovery_id: str,
        evidence_ids: tuple[str, ...],
        rationale: str,
    ) -> RecoveryResult:
        if "recovery:clear" not in self.actor_authorities:
            return RecoveryResult(False, "Actor lacks recovery:clear authority.", evidence_ids)
        if not self.store.is_recovery_required(case_id):
            return RecoveryResult(False, "Case is not recovery-blocked.", evidence_ids)
        if not evidence_ids:
            return RecoveryResult(False, "Independent recovery evidence is required.", evidence_ids)

        observed = self.store.get_case_snapshot(case_id)
        self.store.record_recovery(
            case_id=case_id,
            recovery_id=recovery_id,
            actor=self.actor,
            evidence_ids=evidence_ids,
            rationale=rationale,
            observed_state=observed.token,
        )
        self.store.clear_recovery_required(case_id=case_id, recovery_id=recovery_id)
        self.events.publish(
            "flowbound.case.recovery_cleared",
            {
                "case_id": case_id,
                "recovery_id": recovery_id,
                "observed_state": observed.token,
                "evidence_count": len(evidence_ids),
            },
        )
        return RecoveryResult(True, "Recovery block cleared with explicit authority and evidence.", evidence_ids)
