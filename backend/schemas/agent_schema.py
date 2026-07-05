from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class QaSessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=128)
    pet_id: int | None = None


class QaMessageCreate(BaseModel):
    content: str = Field(..., min_length=1)


class GuideSessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=128)
    pet_id: int | None = None


class GuideMessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=10)


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


class GuideRecommendationResponse(BaseModel):
    product_id: int
    sku_id: int | None = None
    rank: int
    reason: str
    caution: str | None = None
    product: dict[str, Any]


class GuideAnswerResponse(BaseModel):
    session_id: int
    user_message: AgentMessageResponse
    assistant_message: AgentMessageResponse
    recommendations: list[GuideRecommendationResponse]
