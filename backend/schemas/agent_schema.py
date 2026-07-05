from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QaSessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=128)
    pet_id: int | None = None


class QaMessageCreate(BaseModel):
    content: str = Field(..., min_length=1)


class AgentMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    role: str
    content: str
    risk_level: str
    references: str | None = None
    created_at: datetime


class AgentSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    agent_type: str
    title: str | None = None
    pet_id: int | None = None
    messages: list[AgentMessageResponse] = []
    created_at: datetime
    updated_at: datetime


class QaAnswerResponse(BaseModel):
    session_id: int
    user_message: AgentMessageResponse
    assistant_message: AgentMessageResponse
