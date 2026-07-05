"""add pet profile and coin tables

Revision ID: 0007_pet_coin
Revises: 0006_knowledge_rag
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0007_pet_coin"
down_revision: str | None = "0006_knowledge_rag"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "pet_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("pet_type", sa.String(32), nullable=False),
        sa.Column("breed", sa.String(64)),
        sa.Column("gender", sa.String(16)),
        sa.Column("birthday", sa.Date()),
        sa.Column("arrival_date", sa.Date()),
        sa.Column("weight", sa.Float()),
        sa.Column("avatar", sa.String(512)),
        sa.Column("sterilized", sa.Boolean()),
        sa.Column("vaccine_status", sa.String(64)),
        sa.Column("deworm_status", sa.String(64)),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        *timestamps(),
    )
    op.create_index(op.f("ix_pet_profile_user_id"), "pet_profile", ["user_id"])

    op.create_table(
        "pet_growth_record",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pet_profile.id"), nullable=False),
        sa.Column("record_type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(128)),
        sa.Column("content", sa.Text()),
        sa.Column("media_urls", sa.JSON()),
        sa.Column("weight", sa.Float()),
        sa.Column("happened_at", sa.DateTime(timezone=True)),
        *timestamps(),
    )
    op.create_index(op.f("ix_pet_growth_record_user_id"), "pet_growth_record", ["user_id"])
    op.create_index(op.f("ix_pet_growth_record_pet_id"), "pet_growth_record", ["pet_id"])

    op.create_table(
        "pet_health_reminder",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pet_profile.id"), nullable=False),
        sa.Column("reminder_type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("repeat_rule", sa.String(64)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("notes", sa.Text()),
        *timestamps(),
    )
    op.create_index(op.f("ix_pet_health_reminder_user_id"), "pet_health_reminder", ["user_id"])
    op.create_index(op.f("ix_pet_health_reminder_pet_id"), "pet_health_reminder", ["pet_id"])
    op.create_index(op.f("ix_pet_health_reminder_status"), "pet_health_reminder", ["status"])

    op.create_table(
        "pet_album",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pet_profile.id"), nullable=False),
        sa.Column("media_url", sa.String(512), nullable=False),
        sa.Column("media_type", sa.String(32), nullable=False),
        sa.Column("description", sa.String(255)),
        *timestamps(),
    )
    op.create_index(op.f("ix_pet_album_user_id"), "pet_album", ["user_id"])
    op.create_index(op.f("ix_pet_album_pet_id"), "pet_album", ["pet_id"])

    op.create_table(
        "pet_detail_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pet_profile.id"), nullable=False),
        sa.Column("body_size", sa.String(64)),
        sa.Column("health_notes", sa.Text()),
        sa.Column("allergy_notes", sa.Text()),
        sa.Column("diet_preference", sa.Text()),
        sa.Column("product_preference", sa.Text()),
        sa.Column("behavior_notes", sa.Text()),
        sa.Column("care_notes", sa.Text()),
        sa.Column("profile_completeness", sa.Integer(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("pet_id", name="uq_pet_detail_profile_pet_id"),
    )
    op.create_index(op.f("ix_pet_detail_profile_user_id"), "pet_detail_profile", ["user_id"])
    op.create_index(op.f("ix_pet_detail_profile_pet_id"), "pet_detail_profile", ["pet_id"])

    op.create_table(
        "pet_profile_document",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pet_profile.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_snapshot", sa.JSON(), nullable=False),
        sa.Column("profile_completeness", sa.Integer(), nullable=False),
        *timestamps(),
    )
    op.create_index(op.f("ix_pet_profile_document_user_id"), "pet_profile_document", ["user_id"])
    op.create_index(op.f("ix_pet_profile_document_pet_id"), "pet_profile_document", ["pet_id"])

    op.create_table(
        "pet_coin_account",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False),
        sa.Column("frozen_balance", sa.Integer(), nullable=False),
        sa.Column("total_earned", sa.Integer(), nullable=False),
        sa.Column("total_spent", sa.Integer(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("user_id", name="uq_pet_coin_account_user_id"),
    )
    op.create_index(op.f("ix_pet_coin_account_user_id"), "pet_coin_account", ["user_id"])

    op.create_table(
        "pet_coin_log",
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
        sa.UniqueConstraint("idempotency_key", name="uq_pet_coin_log_idempotency_key"),
    )
    for column in ("user_id", "type", "source", "related_id"):
        op.create_index(op.f(f"ix_pet_coin_log_{column}"), "pet_coin_log", [column])

    op.create_table(
        "coin_task",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("reward_amount", sa.Integer(), nullable=False),
        sa.Column("task_type", sa.String(32), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("description", sa.Text()),
        *timestamps(),
    )

    op.create_table(
        "coin_task_record",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("coin_task.id"), nullable=False),
        sa.Column("reward_amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("user_id", "task_id", name="uq_coin_task_record_user_task"),
    )
    op.create_index(op.f("ix_coin_task_record_user_id"), "coin_task_record", ["user_id"])
    op.create_index(op.f("ix_coin_task_record_task_id"), "coin_task_record", ["task_id"])

    op.create_table(
        "daily_checkin",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("checkin_date", sa.Date(), nullable=False),
        sa.Column("reward_amount", sa.Integer(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("user_id", "checkin_date", name="uq_daily_checkin_user_date"),
    )
    op.create_index(op.f("ix_daily_checkin_user_id"), "daily_checkin", ["user_id"])
    op.create_index(op.f("ix_daily_checkin_checkin_date"), "daily_checkin", ["checkin_date"])


def downgrade() -> None:
    for table in (
        "daily_checkin",
        "coin_task_record",
        "coin_task",
        "pet_coin_log",
        "pet_coin_account",
        "pet_profile_document",
        "pet_detail_profile",
        "pet_album",
        "pet_health_reminder",
        "pet_growth_record",
        "pet_profile",
    ):
        op.drop_table(table)
