"""add guide agent recommendations

Revision ID: 0008_guide_agent_recommendation
Revises: 0007_pet_coin
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0008_guide_agent_recommendation"
down_revision: str | None = "0007_pet_coin"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "agent_recommendation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("agent_session.id"), nullable=False),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("agent_message.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=False),
        sa.Column("sku_id", sa.Integer(), sa.ForeignKey("product_sku.id"), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("caution", sa.Text(), nullable=True),
        sa.Column("source", sa.String(32), nullable=False),
        *timestamps(),
    )
    op.create_index(op.f("ix_agent_recommendation_id"), "agent_recommendation", ["id"])
    op.create_index(op.f("ix_agent_recommendation_session_id"), "agent_recommendation", ["session_id"])
    op.create_index(op.f("ix_agent_recommendation_message_id"), "agent_recommendation", ["message_id"])
    op.create_index(op.f("ix_agent_recommendation_user_id"), "agent_recommendation", ["user_id"])
    op.create_index(op.f("ix_agent_recommendation_product_id"), "agent_recommendation", ["product_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_recommendation_product_id"), table_name="agent_recommendation")
    op.drop_index(op.f("ix_agent_recommendation_user_id"), table_name="agent_recommendation")
    op.drop_index(op.f("ix_agent_recommendation_message_id"), table_name="agent_recommendation")
    op.drop_index(op.f("ix_agent_recommendation_session_id"), table_name="agent_recommendation")
    op.drop_index(op.f("ix_agent_recommendation_id"), table_name="agent_recommendation")
    op.drop_table("agent_recommendation")
