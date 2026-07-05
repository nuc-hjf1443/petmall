"""add order and payment tables

Revision ID: 0003_order_payment
Revises: 0002_product_cart_base
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003_order_payment"
down_revision: str | None = "0002_product_cart_base"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_no", sa.String(40), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("merchant_id", sa.Integer(), nullable=False),
        sa.Column("total_amount", sa.Integer(), nullable=False),
        sa.Column("discount_amount", sa.Integer(), nullable=False),
        sa.Column("coin_deduct_amount", sa.Integer(), nullable=False),
        sa.Column("pay_amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("address_snapshot", sa.JSON(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("total_amount >= 0 AND pay_amount >= 0", name="ck_orders_amount_non_negative"),
        sa.UniqueConstraint("order_no"),
    )
    for column in ("order_no", "user_id", "merchant_id", "status"):
        op.create_index(op.f(f"ix_orders_{column}"), "orders", [column])
    op.create_table(
        "order_item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=False),
        sa.Column("sku_id", sa.Integer(), sa.ForeignKey("product_sku.id"), nullable=False),
        sa.Column("product_title", sa.String(255), nullable=False),
        sa.Column("sku_name", sa.String(128), nullable=False),
        sa.Column("sku_specs", sa.JSON(), nullable=False),
        sa.Column("product_image", sa.String(512)),
        sa.Column("unit_price", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("subtotal", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity > 0 AND unit_price >= 0", name="ck_order_item_values"),
    )
    for column in ("order_id", "product_id", "sku_id"):
        op.create_index(op.f(f"ix_order_item_{column}"), "order_item", [column])
    op.create_foreign_key(
        "fk_product_review_order_item_id_order_item",
        "product_review", "order_item", ["order_item_id"], ["id"],
    )
    op.create_table(
        "payment_transaction",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("out_trade_no", sa.String(64), nullable=False),
        sa.Column("business_type", sa.String(32), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("pay_channel", sa.String(32), nullable=False),
        sa.Column("payment_mode", sa.String(32), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("channel_trade_no", sa.String(128)),
        sa.Column("raw_notify", sa.JSON()),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount >= 0", name="ck_payment_amount_non_negative"),
        sa.UniqueConstraint("out_trade_no"),
        sa.UniqueConstraint("business_type", "business_id", name="uq_payment_business"),
    )
    for column in ("out_trade_no", "business_id", "status"):
        op.create_index(op.f(f"ix_payment_transaction_{column}"), "payment_transaction", [column])
    op.create_table(
        "after_sale",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_after_sale_order_id"), "after_sale", ["order_id"])
    op.create_index(op.f("ix_after_sale_user_id"), "after_sale", ["user_id"])
    op.create_table(
        "order_reward_delivery",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False, unique=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_order_reward_delivery_user_id"), "order_reward_delivery", ["user_id"])


def downgrade() -> None:
    op.drop_table("order_reward_delivery")
    op.drop_table("after_sale")
    op.drop_table("payment_transaction")
    op.drop_constraint("fk_product_review_order_item_id_order_item", "product_review", type_="foreignkey")
    op.drop_table("order_item")
    op.drop_table("orders")
