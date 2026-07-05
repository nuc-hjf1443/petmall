from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MerchantQualificationInput(BaseModel):
    qualification_type: str = Field(..., min_length=1, max_length=64)
    file_name: str = Field(..., min_length=1, max_length=255)
    file_url: str = Field(..., min_length=1, max_length=512)
    file_type: str | None = Field(default=None, max_length=64)
    storage_key: str | None = Field(default=None, max_length=512)


class MerchantApplyRequest(BaseModel):
    shop_name: str = Field(..., min_length=1, max_length=128)
    contact_name: str = Field(..., min_length=1, max_length=64)
    contact_phone: str = Field(..., min_length=1, max_length=20)
    business_scope: str = Field(..., min_length=1, max_length=255)
    city: str | None = Field(default=None, max_length=64)
    address: str | None = Field(default=None, max_length=255)
    description: str | None = None
    qualifications: list[MerchantQualificationInput] = Field(default_factory=list)


class MerchantUpdateRequest(BaseModel):
    shop_name: str | None = Field(default=None, min_length=1, max_length=128)
    contact_name: str | None = Field(default=None, min_length=1, max_length=64)
    contact_phone: str | None = Field(default=None, min_length=1, max_length=20)
    business_scope: str | None = Field(default=None, min_length=1, max_length=255)
    city: str | None = Field(default=None, max_length=64)
    address: str | None = Field(default=None, max_length=255)
    description: str | None = None


class MerchantQualificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    qualification_type: str
    file_name: str
    file_url: str
    file_type: str | None = None
    storage_key: str | None = None
    created_at: datetime


class MerchantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_user_id: int
    shop_name: str
    contact_name: str
    contact_phone: str
    business_scope: str
    city: str | None = None
    address: str | None = None
    description: str | None = None
    status: str
    audit_reason: str | None = None
    qualifications: list[MerchantQualificationResponse] = []
    created_at: datetime
    updated_at: datetime


class MerchantDashboardResponse(BaseModel):
    merchant_id: int
    status: str
    pending_product_count: int = 0
    order_count: int = 0


class MerchantAuditDecision(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class MerchantProductStatusRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class MerchantProductDiscountRequest(BaseModel):
    discount_rate: float | None = Field(default=None, gt=0, le=1)
    sku_prices: dict[int, int] = Field(default_factory=dict)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    reason: str | None = Field(default=None, max_length=1000)


class MerchantProductActionResponse(BaseModel):
    product_id: int
    merchant_id: int
    action: str
    status: str


class MerchantProductResponse(BaseModel):
    product: dict[str, Any]
