from __future__ import annotations

import uuid

from .service import AgentActionProposal


class GoogleAdkProposalAgent:
    """Invoke the FlowBound ADK fleet and parse its final structured action proposal."""

    def __init__(self, *, app_name: str = "flowbound", user_id: str = "flowbound-runtime") -> None:
        from google.adk import Runner
        from google.adk.sessions import InMemorySessionService
        from flowbound_agent.agent import root_agent

        self._app_name = app_name
        self._user_id = user_id
        self._sessions = InMemorySessionService()
        self._runner = Runner(agent=root_agent, app_name=app_name, session_service=self._sessions)

    async def propose(self, *, observation: str, predecessor_state: str) -> AgentActionProposal:
        from google.genai import types
        from flowbound_agent.schema import AgentActionProposalSchema

        session_id = f"flowbound-{uuid.uuid4().hex[:16]}"
        await self._sessions.create_session(app_name=self._app_name, user_id=self._user_id, session_id=session_id)
        prompt = (
            f"Authoritative case state for reasoning context: {predecessor_state}\n"
            f"Inspector observation: {observation}\n"
            "Propose one bounded workflow effect. Do not claim or infer execution authority."
        )
        message = types.Content(role="user", parts=[types.Part(text=prompt)])
        final_text: str | None = None
        async for event in self._runner.run_async(user_id=self._user_id, session_id=session_id, new_message=message):
            if event.is_final_response() and event.content and event.content.parts:
                final_text = "".join(part.text or "" for part in event.content.parts)

        if not final_text:
            raise RuntimeError("ADK fleet produced no final action proposal")
        parsed = AgentActionProposalSchema.model_validate_json(final_text)
        return AgentActionProposal(requested_effect=parsed.requested_effect, rationale=parsed.rationale)
