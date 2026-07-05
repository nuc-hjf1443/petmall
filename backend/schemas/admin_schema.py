from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from schemas.auth_schema import TokenResponse


class AdminLoginResponse(TokenResponse):
    is_admin: bool = True


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    email: str | None = None
    nickname: str | None = None
    is_admin: bool
    is_merchant: bool
    is_frozen: bool
    is_deleted: bool
    created_at: datetime


class AdminReasonRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class AdminReportResolveRequest(BaseModel):
    action: str = Field(..., pattern="^(dismiss|take_down)$")
    reason: str | None = Field(default=None, max_length=1000)


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_type: str
    target_id: int
    action: str
    result: str
    reason: str | None = None
    operator_id: int
    created_at: datetime
