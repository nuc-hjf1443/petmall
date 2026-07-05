from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CartItemCreate(BaseModel):
    sku_id: int = Field(..., gt=0)
    quantity: int = Field(default=1, ge=1, le=99)


class CartItemUpdate(BaseModel):
    quantity: int | None = Field(default=None, ge=1, le=99)
    selected: bool | None = None


class CartProductResponse(BaseModel):
    id: int
    merchant_id: int
    title: str
    cover_image: str | None = None
    status: str


class CartSkuResponse(BaseModel):
    id: int
    sku_code: str
    name: str
    specs: dict[str, Any]
    price: int
    stock: int
    is_enabled: bool


class CartItemResponse(BaseModel):
    id: int
    quantity: int
    selected: bool
    available: bool
    subtotal: int
    product: CartProductResponse
    sku: CartSkuResponse
    created_at: datetime
    updated_at: datetime
