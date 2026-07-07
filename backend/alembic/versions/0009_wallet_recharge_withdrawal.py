"""add wallet recharge and withdrawal tables

Revision ID: 0009_wallet_recharge_withdrawal
Revises: 0008_guide_agent_recommendation
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0009_wallet_recharge_withdrawal"
down_revision: str | None = "0008_guide_agent_recommendation"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "wallet_account",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False),
        sa.Column("frozen_balance", sa.Integer(), nullable=False),
        sa.Column("total_recharged", sa.Integer(), nullable=False),
        sa.Column("total_withdrawn", sa.Integer(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("user_id", name="uq_wallet_account_user_id"),
        sa.CheckConstraint("balance >= 0 AND frozen_balance >= 0", name="ck_wallet_account_non_negative"),
    )
    op.create_index(op.f("ix_wallet_account_user_id"), "wallet_account", ["user_id"])

    op.create_table(
        "wallet_recharge",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recharge_no", sa.String(40), nullable=False, unique=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.CheckConstraint("amount > 0", name="ck_wallet_recharge_amount_positive"),
    )
    op.create_index(op.f("ix_wallet_recharge_recharge_no"), "wallet_recharge", ["recharge_no"])
    op.create_index(op.f("ix_wallet_recharge_user_id"), "wallet_recharge", ["user_id"])
    op.create_index(op.f("ix_wallet_recharge_status"), "wallet_recharge", ["status"])

    op.create_table(
        "wallet_transaction",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("change_amount", sa.Integer(), nullable=False),
        sa.Column("balance_before", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("frozen_before", sa.Integer(), nullable=False),
        sa.Column("frozen_after", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("related_id", sa.Integer()),
        sa.Column("idempotency_key", sa.String(128)),
        sa.Column("remark", sa.Text()),
        *timestamps(),
        sa.UniqueConstraint("idempotency_key", name="uq_wallet_transaction_idempotency_key"),
        sa.CheckConstraint(
            "balance_before >= 0 AND balance_after >= 0",
            name="ck_wallet_transaction_balance_non_negative",
        ),
        sa.CheckConstraint(
            "frozen_before >= 0 AND frozen_after >= 0",
            name="ck_wallet_transaction_frozen_non_negative",
        ),
    )
    for column in ("user_id", "type", "source", "related_id"):
        op.create_index(op.f(f"ix_wallet_transaction_{column}"), "wallet_transaction", [column])

    op.create_table(
        "withdrawal_request",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("withdrawal_no", sa.String(40), nullable=False, unique=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("account_name", sa.String(64), nullable=False),
        sa.Column("alipay_account", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("user.id")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.CheckConstraint("amount > 0", name="ck_withdrawal_request_amount_positive"),
    )
    op.create_index(op.f("ix_withdrawal_request_withdrawal_no"), "withdrawal_request", ["withdrawal_no"])
    op.create_index(op.f("ix_withdrawal_request_user_id"), "withdrawal_request", ["user_id"])
    op.create_index(op.f("ix_withdrawal_request_status"), "withdrawal_request", ["status"])
    op.create_index(op.f("ix_withdrawal_request_reviewed_by"), "withdrawal_request", ["reviewed_by"])


def downgrade() -> None:
    op.drop_table("withdrawal_request")
    op.drop_table("wallet_transaction")
    op.drop_table("wallet_recharge")
    op.drop_table("wallet_account")
