"""create adoption merchant admin agent tables

Revision ID: 0002_c_adoption_merchant_admin_agent
Revises: 0001_user_auth_profile_address
Create Date: 2026-07-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0002_c_adoption_merchant_admin_agent"
down_revision: str | None = "0001_user_auth_profile_address"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "adoption_pet",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("publisher_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("species", sa.String(length=32), nullable=False),
        sa.Column("breed", sa.String(length=64), nullable=True),
        sa.Column("age_text", sa.String(length=64), nullable=True),
        sa.Column("gender", sa.String(length=16), nullable=True),
        sa.Column("city", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("health_status", sa.Text(), nullable=True),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("cover_image", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["publisher_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_adoption_pet_id"), "adoption_pet", ["id"], unique=False)
    op.create_index(op.f("ix_adoption_pet_publisher_id"), "adoption_pet", ["publisher_id"], unique=False)
    op.create_index(op.f("ix_adoption_pet_status"), "adoption_pet", ["status"], unique=False)

    op.create_table(
        "merchant",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("shop_name", sa.String(length=128), nullable=False),
        sa.Column("contact_name", sa.String(length=64), nullable=False),
        sa.Column("contact_phone", sa.String(length=20), nullable=False),
        sa.Column("business_scope", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=64), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("audit_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_user_id"),
    )
    op.create_index(op.f("ix_merchant_id"), "merchant", ["id"], unique=False)
    op.create_index(op.f("ix_merchant_owner_user_id"), "merchant", ["owner_user_id"], unique=False)
    op.create_index(op.f("ix_merchant_status"), "merchant", ["status"], unique=False)

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("operator_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["operator_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_log_id"), "audit_log", ["id"], unique=False)
    op.create_index(op.f("ix_audit_log_operator_id"), "audit_log", ["operator_id"], unique=False)
    op.create_index(op.f("ix_audit_log_target_id"), "audit_log", ["target_id"], unique=False)
    op.create_index(op.f("ix_audit_log_target_type"), "audit_log", ["target_type"], unique=False)

    op.create_table(
        "operation_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("operator_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=True),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["operator_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_operation_log_id"), "operation_log", ["id"], unique=False)
    op.create_index(op.f("ix_operation_log_operator_id"), "operation_log", ["operator_id"], unique=False)

    op.create_table(
        "admin_action_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admin_action_log_admin_id"), "admin_action_log", ["admin_id"], unique=False)
    op.create_index(op.f("ix_admin_action_log_id"), "admin_action_log", ["id"], unique=False)

    op.create_table(
        "agent_session",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("agent_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=True),
        sa.Column("pet_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_session_agent_type"), "agent_session", ["agent_type"], unique=False)
    op.create_index(op.f("ix_agent_session_id"), "agent_session", ["id"], unique=False)
    op.create_index(op.f("ix_agent_session_user_id"), "agent_session", ["user_id"], unique=False)

    op.create_table(
        "adoption_application",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("adoption_pet_id", sa.Integer(), nullable=False),
        sa.Column("applicant_id", sa.Integer(), nullable=False),
        sa.Column("contact_name", sa.String(length=64), nullable=False),
        sa.Column("contact_phone", sa.String(length=20), nullable=False),
        sa.Column("living_city", sa.String(length=64), nullable=False),
        sa.Column("living_condition", sa.String(length=128), nullable=False),
        sa.Column("experience", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("audit_reason", sa.Text(), nullable=True),
        sa.Column("audited_by", sa.Integer(), nullable=True),
        sa.Column("audited_at", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["adoption_pet_id"], ["adoption_pet.id"]),
        sa.ForeignKeyConstraint(["applicant_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["audited_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("adoption_pet_id", "applicant_id", name="uq_adoption_application_pet_applicant"),
    )
    op.create_index(op.f("ix_adoption_application_adoption_pet_id"), "adoption_application", ["adoption_pet_id"], unique=False)
    op.create_index(op.f("ix_adoption_application_applicant_id"), "adoption_application", ["applicant_id"], unique=False)
    op.create_index(op.f("ix_adoption_application_id"), "adoption_application", ["id"], unique=False)
    op.create_index(op.f("ix_adoption_application_status"), "adoption_application", ["status"], unique=False)

    op.create_table(
        "merchant_qualification",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("merchant_id", sa.Integer(), nullable=False),
        sa.Column("qualification_type", sa.String(length=64), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_url", sa.String(length=512), nullable=False),
        sa.Column("file_type", sa.String(length=64), nullable=True),
        sa.Column("storage_key", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchant.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_merchant_qualification_id"), "merchant_qualification", ["id"], unique=False)
    op.create_index(op.f("ix_merchant_qualification_merchant_id"), "merchant_qualification", ["merchant_id"], unique=False)

    op.create_table(
        "merchant_staff",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("merchant_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchant.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("merchant_id", "user_id", name="uq_merchant_staff_merchant_user"),
    )
    op.create_index(op.f("ix_merchant_staff_id"), "merchant_staff", ["id"], unique=False)
    op.create_index(op.f("ix_merchant_staff_merchant_id"), "merchant_staff", ["merchant_id"], unique=False)
    op.create_index(op.f("ix_merchant_staff_user_id"), "merchant_staff", ["user_id"], unique=False)

    op.create_table(
        "adoption_follow_up",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("operator_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("result", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["adoption_application.id"]),
        sa.ForeignKeyConstraint(["operator_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_adoption_follow_up_application_id"), "adoption_follow_up", ["application_id"], unique=False)
    op.create_index(op.f("ix_adoption_follow_up_id"), "adoption_follow_up", ["id"], unique=False)
    op.create_index(op.f("ix_adoption_follow_up_operator_id"), "adoption_follow_up", ["operator_id"], unique=False)

    op.create_table(
        "agent_message",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("references", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["agent_session.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_message_id"), "agent_message", ["id"], unique=False)
    op.create_index(op.f("ix_agent_message_session_id"), "agent_message", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_message_session_id"), table_name="agent_message")
    op.drop_index(op.f("ix_agent_message_id"), table_name="agent_message")
    op.drop_table("agent_message")
    op.drop_index(op.f("ix_adoption_follow_up_operator_id"), table_name="adoption_follow_up")
    op.drop_index(op.f("ix_adoption_follow_up_id"), table_name="adoption_follow_up")
    op.drop_index(op.f("ix_adoption_follow_up_application_id"), table_name="adoption_follow_up")
    op.drop_table("adoption_follow_up")
    op.drop_index(op.f("ix_merchant_staff_user_id"), table_name="merchant_staff")
    op.drop_index(op.f("ix_merchant_staff_merchant_id"), table_name="merchant_staff")
    op.drop_index(op.f("ix_merchant_staff_id"), table_name="merchant_staff")
    op.drop_table("merchant_staff")
    op.drop_index(op.f("ix_merchant_qualification_merchant_id"), table_name="merchant_qualification")
    op.drop_index(op.f("ix_merchant_qualification_id"), table_name="merchant_qualification")
    op.drop_table("merchant_qualification")
    op.drop_index(op.f("ix_adoption_application_status"), table_name="adoption_application")
    op.drop_index(op.f("ix_adoption_application_id"), table_name="adoption_application")
    op.drop_index(op.f("ix_adoption_application_applicant_id"), table_name="adoption_application")
    op.drop_index(op.f("ix_adoption_application_adoption_pet_id"), table_name="adoption_application")
    op.drop_table("adoption_application")
    op.drop_index(op.f("ix_agent_session_user_id"), table_name="agent_session")
    op.drop_index(op.f("ix_agent_session_id"), table_name="agent_session")
    op.drop_index(op.f("ix_agent_session_agent_type"), table_name="agent_session")
    op.drop_table("agent_session")
    op.drop_index(op.f("ix_admin_action_log_id"), table_name="admin_action_log")
    op.drop_index(op.f("ix_admin_action_log_admin_id"), table_name="admin_action_log")
    op.drop_table("admin_action_log")
    op.drop_index(op.f("ix_operation_log_operator_id"), table_name="operation_log")
    op.drop_index(op.f("ix_operation_log_id"), table_name="operation_log")
    op.drop_table("operation_log")
    op.drop_index(op.f("ix_audit_log_target_type"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_target_id"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_operator_id"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_id"), table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index(op.f("ix_merchant_status"), table_name="merchant")
    op.drop_index(op.f("ix_merchant_owner_user_id"), table_name="merchant")
    op.drop_index(op.f("ix_merchant_id"), table_name="merchant")
    op.drop_table("merchant")
    op.drop_index(op.f("ix_adoption_pet_status"), table_name="adoption_pet")
    op.drop_index(op.f("ix_adoption_pet_publisher_id"), table_name="adoption_pet")
    op.drop_index(op.f("ix_adoption_pet_id"), table_name="adoption_pet")
    op.drop_table("adoption_pet")
