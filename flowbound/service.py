from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .workflow import EventPublisher, GovernedStore, TransitionOutcome, govern_and_execute


@dataclass(frozen=True)
class AgentActionProposal:
    requested_effect: str
    rationale: str


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
    def __init__(self, *, agent: ProposalAgent, store: GovernedStore, events: EventPublisher, actor: str, actor_authorities: frozenset[str]) -> None:
        self.agent = agent
        self.store = store
        self.events = events
        self.actor = actor
        self.actor_authorities = actor_authorities

    async def run_case(
        self,
        *,
        case_id: str,
        transition_id: str,
        observation: str,
        evidence_trusted: bool,
        human_approval_present: bool,
        evidence_ids: tuple[str, ...] = (),
    ) -> tuple[AgentActionProposal, TransitionOutcome]:
        if self.store.is_recovery_required(case_id):
            raise RuntimeError(f"Case {case_id} is blocked pending independent recovery evidence")

        authorized_predecessor = self.store.get_case_snapshot(case_id)
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
            evidence_trusted=evidence_trusted,
            human_approval_present=human_approval_present,
            store=self.store,
            events=self.events,
            evidence_ids=evidence_ids,
            originating_need=observation,
            agent_rationale=agent_proposal.rationale,
        )
        return agent_proposal, outcome
