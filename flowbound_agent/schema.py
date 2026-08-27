from typing import Literal

from pydantic import BaseModel, Field


class AgentActionProposalSchema(BaseModel):
    requested_effect: Literal[
        "CREATE_REMEDIATION_TASK",
        "SCHEDULE_FOLLOW_UP",
        "CLOSE_CASE",
    ]
    rationale: str = Field(min_length=1, max_length=500)
