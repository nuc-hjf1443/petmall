"""create user auth profile address tables

Revision ID: 0001_user_auth_profile_address
Revises:
Create Date: 2026-07-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001_user_auth_profile_address"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("nickname", sa.String(length=64), nullable=True),
        sa.Column("avatar", sa.String(length=512), nullable=True),
        sa.Column("city", sa.String(length=64), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("is_merchant", sa.Boolean(), nullable=False),
        sa.Column("is_frozen", sa.Boolean(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("token_version", sa.Integer(), nullable=False),
        sa.Column("real_name_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_id"), "user", ["id"], unique=False)
    op.create_index(op.f("ix_user_phone"), "user", ["phone"], unique=True)
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)

    op.create_table(
        "user_profile",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("pet_experience", sa.String(length=64), nullable=True),
        sa.Column("living_city", sa.String(length=64), nullable=True),
        sa.Column("living_environment", sa.String(length=128), nullable=True),
        sa.Column("budget_preference", sa.String(length=128), nullable=True),
        sa.Column("preferred_categories", sa.Text(), nullable=True),
        sa.Column("feeding_philosophy", sa.Text(), nullable=True),
        sa.Column("allergy_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_user_profile_id"), "user_profile", ["id"], unique=False)
    op.create_index(op.f("ix_user_profile_user_id"), "user_profile", ["user_id"], unique=False)

    op.create_table(
        "user_address",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("receiver_name", sa.String(length=64), nullable=False),
        sa.Column("receiver_phone", sa.String(length=20), nullable=False),
        sa.Column("province", sa.String(length=64), nullable=False),
        sa.Column("city", sa.String(length=64), nullable=False),
        sa.Column("district", sa.String(length=64), nullable=False),
        sa.Column("detail_address", sa.String(length=255), nullable=False),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "id", name="uq_user_address_user_id_id"),
    )
    op.create_index(op.f("ix_user_address_id"), "user_address", ["id"], unique=False)
    op.create_index(op.f("ix_user_address_user_id"), "user_address", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_address_user_id"), table_name="user_address")
    op.drop_index(op.f("ix_user_address_id"), table_name="user_address")
    op.drop_table("user_address")

    op.drop_index(op.f("ix_user_profile_user_id"), table_name="user_profile")
    op.drop_index(op.f("ix_user_profile_id"), table_name="user_profile")
    op.drop_table("user_profile")

    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_index(op.f("ix_user_phone"), table_name="user")
    op.drop_index(op.f("ix_user_id"), table_name="user")
    op.drop_table("user")
