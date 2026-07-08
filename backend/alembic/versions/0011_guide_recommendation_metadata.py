"""add guide recommendation metadata

Revision ID: 0011_guide_recommendation_metadata
Revises: 0010_product_brand
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0011_guide_recommendation_metadata"
down_revision: str | None = "0010_product_brand"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _column_exists(table_name, column.name):
        op.add_column(table_name, column)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    if _column_exists(table_name, column_name):
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    _add_column_if_missing("agent_session", sa.Column("context_summary", sa.Text(), nullable=True))
    _add_column_if_missing("agent_recommendation", sa.Column("source_detail", sa.String(64), nullable=True))
    _add_column_if_missing("agent_recommendation", sa.Column("score", sa.Float(), nullable=True))
    _add_column_if_missing("agent_recommendation", sa.Column("matched_pet_fields", sa.Text(), nullable=True))


def downgrade() -> None:
    _drop_column_if_exists("agent_recommendation", "matched_pet_fields")
    _drop_column_if_exists("agent_recommendation", "score")
    _drop_column_if_exists("agent_recommendation", "source_detail")
    _drop_column_if_exists("agent_session", "context_summary")

