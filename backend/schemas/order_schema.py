from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    address_id: int = Field(..., gt=0)
    cart_item_ids: list[int] = Field(..., min_length=1)


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    sku_id: int
    product_title: str
    sku_name: str
    sku_specs: dict[str, Any]
    product_image: str | None
    unit_price: int
    quantity: int
    subtotal: int


class OrderResponse(BaseModel):
    id: int
    order_no: str
    merchant_id: int
    total_amount: int
    discount_amount: int
    coin_deduct_amount: int
    pay_amount: int
    status: str
    address_snapshot: dict[str, Any]
    paid_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    items: list[OrderItemResponse]


class PaymentResponse(BaseModel):
    out_trade_no: str
    order_id: int
    amount: int
    status: str
    payment_mode: str
    pay_url: str | None = None
    channel_trade_no: str | None = None
