from datetime import datetime

from pydantic import BaseModel, Field


class SupportMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class SupportStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|resolved)$")


class SupportMessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    content: str
    created_at: datetime


class SupportConversationResponse(BaseModel):
    id: int
    type: str
    status: str
    user_id: int
    merchant_id: int | None = None
    merchant_name: str | None = None
    adoption_pet_id: int | None = None
    adoption_pet_name: str | None = None
    adoption_application_id: int | None = None
    assigned_to_platform: bool = False
    last_message_at: datetime
    created_at: datetime
    messages: list[SupportMessageResponse] = []


class SupportConversationListResponse(BaseModel):
    items: list[SupportConversationResponse]
    total: int
    page: int
    page_size: int
