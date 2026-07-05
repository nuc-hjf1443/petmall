"""add community tables

Revision ID: 0005_community
Revises: 0004_order_payment
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0005_community"
down_revision: str | None = "0004_order_payment"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "post",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("content", sa.Text()),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("moderation_reason", sa.Text()),
        *timestamps(),
    )
    op.create_index(op.f("ix_post_user_id"), "post", ["user_id"])
    op.create_index(op.f("ix_post_status"), "post", ["status"])
    op.create_table(
        "post_media",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("post.id"), nullable=False),
        sa.Column("media_type", sa.String(16), nullable=False),
        sa.Column("file_url", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        *timestamps(),
    )
    op.create_index(op.f("ix_post_media_post_id"), "post_media", ["post_id"])
    op.create_table(
        "post_comment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("post.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("post_comment.id")),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        *timestamps(),
    )
    for column in ("post_id", "user_id", "parent_id"):
        op.create_index(op.f(f"ix_post_comment_{column}"), "post_comment", [column])
    for table in ("post_like", "post_favorite"):
        op.create_table(
            table,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
            sa.Column("post_id", sa.Integer(), sa.ForeignKey("post.id"), nullable=False),
            *timestamps(),
            sa.UniqueConstraint("user_id", "post_id", name=f"uq_{table}_user_post"),
        )
        op.create_index(op.f(f"ix_{table}_user_id"), table, ["user_id"])
        op.create_index(op.f(f"ix_{table}_post_id"), table, ["post_id"])
    op.create_table(
        "topic",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "post_topic",
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("post.id"), primary_key=True),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topic.id"), primary_key=True),
        sa.UniqueConstraint("post_id", "topic_id", name="uq_post_topic"),
    )
    op.create_table(
        "follow",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("follower_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("followed_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("follower_id", "followed_id", name="uq_follow_pair"),
    )
    op.create_index(op.f("ix_follow_follower_id"), "follow", ["follower_id"])
    op.create_index(op.f("ix_follow_followed_id"), "follow", ["followed_id"])
    op.create_table(
        "report",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reporter_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("action", sa.String(32)),
        sa.Column("resolution_reason", sa.Text()),
        sa.Column("resolved_by", sa.Integer(), sa.ForeignKey("user.id")),
        *timestamps(),
        sa.UniqueConstraint("reporter_id", "target_type", "target_id", name="uq_reporter_target"),
    )
    for column in ("reporter_id", "target_type", "target_id", "status"):
        op.create_index(op.f(f"ix_report_{column}"), "report", [column])


def downgrade() -> None:
    for table in (
        "report", "follow", "post_topic", "topic", "post_favorite",
        "post_like", "post_comment", "post_media", "post",
    ):
        op.drop_table(table)
