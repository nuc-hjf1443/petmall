"""add guide recommendation metadata

Revision ID: 0010_guide_recommendation_metadata
Revises: 0009_wallet_recharge_withdrawal
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0010_guide_recommendation_metadata"
down_revision: str | None = "0009_wallet_recharge_withdrawal"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("agent_session", sa.Column("context_summary", sa.Text(), nullable=True))
    op.add_column("agent_recommendation", sa.Column("source_detail", sa.String(64), nullable=True))
    op.add_column("agent_recommendation", sa.Column("score", sa.Float(), nullable=True))
    op.add_column("agent_recommendation", sa.Column("matched_pet_fields", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_recommendation", "matched_pet_fields")
    op.drop_column("agent_recommendation", "score")
    op.drop_column("agent_recommendation", "source_detail")
    op.drop_column("agent_session", "context_summary")

