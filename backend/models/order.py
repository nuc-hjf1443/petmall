from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class OrderStatus(StrEnum):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    PENDING_SHIPMENT = "pending_shipment"
    SHIPPED = "shipped"
    PENDING_RECEIPT = "pending_receipt"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    AFTER_SALE = "after_sale"
    REFUNDED = "refunded"


class PaymentStatus(StrEnum):
    CREATED = "created"
    PAYING = "paying"
    PAID = "paid"
    CLOSED = "closed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("total_amount >= 0 AND pay_amount >= 0", name="ck_orders_amount_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    merchant_id: Mapped[int] = mapped_column(Integer, index=True)
    total_amount: Mapped[int] = mapped_column(Integer)
    discount_amount: Mapped[int] = mapped_column(Integer, default=0)
    coin_deduct_amount: Mapped[int] = mapped_column(Integer, default=0)
    pay_amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default=OrderStatus.PENDING_PAYMENT.value, index=True)
    address_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_item"
    __table_args__ = (CheckConstraint("quantity > 0 AND unit_price >= 0", name="ck_order_item_values"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("product_sku.id"), index=True)
    product_title: Mapped[str] = mapped_column(String(255))
    sku_name: Mapped[str] = mapped_column(String(128))
    sku_specs: Mapped[dict[str, Any]] = mapped_column(JSON)
    product_image: Mapped[str | None] = mapped_column(String(512))
    unit_price: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer)
    subtotal: Mapped[int] = mapped_column(Integer)
    order: Mapped[Order] = relationship(back_populates="items")


class PaymentTransaction(Base, TimestampMixin):
    __tablename__ = "payment_transaction"
    __table_args__ = (
        UniqueConstraint("business_type", "business_id", name="uq_payment_business"),
        CheckConstraint("amount >= 0", name="ck_payment_amount_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    out_trade_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    business_type: Mapped[str] = mapped_column(String(32))
    business_id: Mapped[int] = mapped_column(Integer, index=True)
    pay_channel: Mapped[str] = mapped_column(String(32))
    payment_mode: Mapped[str] = mapped_column(String(32))
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default=PaymentStatus.CREATED.value, index=True)
    channel_trade_no: Mapped[str | None] = mapped_column(String(128))
    raw_notify: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AfterSale(Base, TimestampMixin):
    __tablename__ = "after_sale"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    reason: Mapped[str | None] = mapped_column(Text)


class OrderRewardDelivery(Base, TimestampMixin):
    __tablename__ = "order_reward_delivery"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
