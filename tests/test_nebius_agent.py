import asyncio
from types import SimpleNamespace

from flowbound.events import InMemoryEventPublisher
from flowbound.nebius_client import NebiusNemotronProposalAgent
from flowbound.service import FlowBoundService
from flowbound.state import InMemoryCaseStore


class FakeCompletions:
    def __init__(self):
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        index = len(self.calls)
        if index == 1:
            content = "Observed: rear exit door does not latch."
        elif index == 2:
            content = "Evidence is concrete; no authority is implied."
        else:
            content = (
                '{"requested_effect":"CREATE_REMEDIATION_TASK",'
                '"rationale":"The observed defect warrants a remediation task proposal."}'
            )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )


class FakeClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=FakeCompletions())


def test_nebius_fleet_uses_three_bounded_model_calls():
    client = FakeClient()
    agent = NebiusNemotronProposalAgent(
        client=client,
        model="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
        evidence_model="nvidia/nemotron-3-super-120b-a12b",
    )

    proposal = asyncio.run(
        agent.propose(
            observation="Rear exit door does not latch.",
            predecessor_state="OPEN",
        )
    )

    assert proposal.requested_effect == "CREATE_REMEDIATION_TASK"
    assert proposal.provider == "nebius-token-factory"
    assert proposal.model == "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
    assert proposal.trace_id.startswith("nebius-")
    assert [call["model"] for call in client.chat.completions.calls] == [
        "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
        "nvidia/nemotron-3-super-120b-a12b",
        "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
    ]


def test_nebius_provider_and_model_are_written_into_decision_provenance():
    client = FakeClient()
    agent = NebiusNemotronProposalAgent(client=client)
    store = InMemoryCaseStore()
    store.create_case("n1")
    service = FlowBoundService(
        agent=agent,
        store=store,
        events=InMemoryEventPublisher(),
        actor="flowbound_action_agent",
        actor_authorities=frozenset({"remediation:create"}),
    )

    proposal, outcome = asyncio.run(
        service.run_case(
            case_id="n1",
            transition_id="tx-nebius",
            observation="Rear exit door does not latch.",
            human_approval_present=False,
        )
    )

    assert outcome.execution and outcome.execution.applied
    decision = store.decisions[("n1", "tx-nebius")]
    persisted = decision["proposal"]
    assert persisted.agent_provider == "nebius-token-factory"
    assert persisted.agent_model == proposal.model
    assert persisted.agent_trace_id == proposal.trace_id
