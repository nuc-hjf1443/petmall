from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from schemas.auth_schema import TokenResponse
from schemas.order_schema import OrderItemResponse


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


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]
    total: int
    page: int
    page_size: int


class AdminReasonRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class AdminReportResolveRequest(BaseModel):
    action: str = Field(..., pattern="^(dismiss|take_down)$")
    reason: str | None = Field(default=None, max_length=1000)


class AdminPetResponse(BaseModel):
    id: int
    user_id: int
    owner_phone: str
    owner_nickname: str | None = None
    name: str
    pet_type: str
    breed: str | None = None
    gender: str | None = None
    avatar: str | None = None
    profile_completeness: int | None = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class AdminPetListResponse(BaseModel):
    items: list[AdminPetResponse]
    total: int
    page: int
    page_size: int


class AdminOrderResponse(BaseModel):
    id: int
    order_no: str
    user_id: int
    user_phone: str | None = None
    merchant_id: int
    merchant_name: str | None = None
    total_amount: int
    discount_amount: int
    coin_deduct_amount: int
    pay_amount: int
    status: str
    payment_status: str | None = None
    payment_mode: str | None = None
    out_trade_no: str | None = None
    address_snapshot: dict
    paid_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime
    items: list[OrderItemResponse]


class AdminOrderListResponse(BaseModel):
    items: list[AdminOrderResponse]
    total: int
    page: int
    page_size: int


class AdminOverviewResponse(BaseModel):
    gmv: int
    order_count: int
    paid_order_count: int
    pet_count: int
    user_count: int
    merchant_count: int


class AdminOrderTrendItem(BaseModel):
    date: str
    order_count: int
    gmv: int


class AdminOrderTrendResponse(BaseModel):
    items: list[AdminOrderTrendItem]


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
