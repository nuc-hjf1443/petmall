"""add support conversations and favorites

Revision ID: 0012_support_favorites_follow
Revises: 0011_guide_meta
Create Date: 2026-07-08
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0012_support_favorites_follow"
down_revision: str | None = "0011_guide_meta"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_favorite",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "product_id", name="uq_product_favorite_user_product"),
    )
    op.create_index(op.f("ix_product_favorite_id"), "product_favorite", ["id"], unique=False)
    op.create_index(op.f("ix_product_favorite_product_id"), "product_favorite", ["product_id"], unique=False)
    op.create_index(op.f("ix_product_favorite_user_id"), "product_favorite", ["user_id"], unique=False)

    op.create_table(
        "merchant_follow",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("merchant_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchant.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "merchant_id", name="uq_merchant_follow_user_merchant"),
    )
    op.create_index(op.f("ix_merchant_follow_id"), "merchant_follow", ["id"], unique=False)
    op.create_index(op.f("ix_merchant_follow_merchant_id"), "merchant_follow", ["merchant_id"], unique=False)
    op.create_index(op.f("ix_merchant_follow_user_id"), "merchant_follow", ["user_id"], unique=False)

    op.create_table(
        "support_conversation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("merchant_id", sa.Integer(), nullable=True),
        sa.Column("adoption_pet_id", sa.Integer(), nullable=True),
        sa.Column("adoption_application_id", sa.Integer(), nullable=True),
        sa.Column("assigned_to_platform", sa.Boolean(), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'resolved')", name="ck_support_conversation_status_valid"),
        sa.CheckConstraint("type IN ('platform', 'merchant', 'adoption')", name="ck_support_conversation_type_valid"),
        sa.ForeignKeyConstraint(["adoption_application_id"], ["adoption_application.id"]),
        sa.ForeignKeyConstraint(["adoption_pet_id"], ["adoption_pet.id"]),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchant.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_support_conversation_id"), "support_conversation", ["id"], unique=False)
    op.create_index(op.f("ix_support_conversation_type"), "support_conversation", ["type"], unique=False)
    op.create_index(op.f("ix_support_conversation_status"), "support_conversation", ["status"], unique=False)
    op.create_index(op.f("ix_support_conversation_user_id"), "support_conversation", ["user_id"], unique=False)
    op.create_index(op.f("ix_support_conversation_merchant_id"), "support_conversation", ["merchant_id"], unique=False)
    op.create_index(op.f("ix_support_conversation_adoption_pet_id"), "support_conversation", ["adoption_pet_id"], unique=False)
    op.create_index(
        op.f("ix_support_conversation_adoption_application_id"),
        "support_conversation",
        ["adoption_application_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_conversation_assigned_to_platform"),
        "support_conversation",
        ["assigned_to_platform"],
        unique=False,
    )
    op.create_index(
        "ix_support_conversation_user_type",
        "support_conversation",
        ["user_id", "type"],
        unique=False,
    )
    op.create_index(
        "ix_support_conversation_merchant_status",
        "support_conversation",
        ["merchant_id", "status"],
        unique=False,
    )

    op.create_table(
        "support_message",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["support_conversation.id"]),
        sa.ForeignKeyConstraint(["sender_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_support_message_id"), "support_message", ["id"], unique=False)
    op.create_index(op.f("ix_support_message_conversation_id"), "support_message", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_support_message_sender_id"), "support_message", ["sender_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_support_message_sender_id"), table_name="support_message")
    op.drop_index(op.f("ix_support_message_conversation_id"), table_name="support_message")
    op.drop_index(op.f("ix_support_message_id"), table_name="support_message")
    op.drop_table("support_message")

    op.drop_index("ix_support_conversation_merchant_status", table_name="support_conversation")
    op.drop_index("ix_support_conversation_user_type", table_name="support_conversation")
    op.drop_index(op.f("ix_support_conversation_assigned_to_platform"), table_name="support_conversation")
    op.drop_index(op.f("ix_support_conversation_adoption_application_id"), table_name="support_conversation")
    op.drop_index(op.f("ix_support_conversation_adoption_pet_id"), table_name="support_conversation")
    op.drop_index(op.f("ix_support_conversation_merchant_id"), table_name="support_conversation")
    op.drop_index(op.f("ix_support_conversation_user_id"), table_name="support_conversation")
    op.drop_index(op.f("ix_support_conversation_status"), table_name="support_conversation")
    op.drop_index(op.f("ix_support_conversation_type"), table_name="support_conversation")
    op.drop_index(op.f("ix_support_conversation_id"), table_name="support_conversation")
    op.drop_table("support_conversation")

    op.drop_index(op.f("ix_merchant_follow_user_id"), table_name="merchant_follow")
    op.drop_index(op.f("ix_merchant_follow_merchant_id"), table_name="merchant_follow")
    op.drop_index(op.f("ix_merchant_follow_id"), table_name="merchant_follow")
    op.drop_table("merchant_follow")

    op.drop_index(op.f("ix_product_favorite_user_id"), table_name="product_favorite")
    op.drop_index(op.f("ix_product_favorite_product_id"), table_name="product_favorite")
    op.drop_index(op.f("ix_product_favorite_id"), table_name="product_favorite")
    op.drop_table("product_favorite")
