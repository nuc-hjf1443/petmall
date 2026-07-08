"""add product brand

Revision ID: 0010_product_brand
Revises: 0009_wallet_recharge_withdrawal
Create Date: 2026-07-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0010_product_brand"
down_revision: str | None = "0009_wallet_recharge_withdrawal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("product", sa.Column("brand", sa.String(length=100), nullable=True))
    op.create_index(op.f("ix_product_brand"), "product", ["brand"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_product_brand"), table_name="product")
    op.drop_column("product", "brand")
