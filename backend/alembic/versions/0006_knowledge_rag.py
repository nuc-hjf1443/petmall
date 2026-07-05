"""add knowledge and rag tables

Revision ID: 0006_knowledge_rag
Revises: 0005_community
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0006_knowledge_rag"
down_revision: str | None = "0005_community"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "knowledge_base",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id")),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("scope", sa.String(16), nullable=False),
        *timestamps(),
    )
    op.create_index(op.f("ix_knowledge_base_user_id"), "knowledge_base", ["user_id"])
    op.create_index(op.f("ix_knowledge_base_scope"), "knowledge_base", ["scope"])
    op.create_table(
        "knowledge_document",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("knowledge_base_id", sa.Integer(), sa.ForeignKey("knowledge_base.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id")),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(16), nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("pet_id", sa.Integer()),
        sa.Column("source_snapshot", sa.JSON()),
        sa.Column("parse_status", sa.String(32), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("index_version", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text()),
        *timestamps(),
    )
    for column in ("knowledge_base_id", "user_id", "pet_id", "parse_status"):
        op.create_index(op.f(f"ix_knowledge_document_{column}"), "knowledge_document", [column])
    op.create_table(
        "knowledge_chunk",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("knowledge_base_id", sa.Integer(), sa.ForeignKey("knowledge_base.id"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("knowledge_document.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id")),
        sa.Column("index_version", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("vector_id", sa.String(128), nullable=False, unique=True),
        sa.Column("content", sa.Text(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("document_id", "index_version", "chunk_index", name="uq_document_chunk_version"),
    )
    for column in ("knowledge_base_id", "document_id", "user_id"):
        op.create_index(op.f(f"ix_knowledge_chunk_{column}"), "knowledge_chunk", [column])
    op.create_table(
        "rag_retrieval_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id")),
        sa.Column("knowledge_base_id", sa.Integer()),
        sa.Column("query_text", sa.String(500), nullable=False),
        sa.Column("results", sa.JSON(), nullable=False),
        sa.Column("caller", sa.String(64), nullable=False),
        *timestamps(),
    )
    op.create_index(op.f("ix_rag_retrieval_log_user_id"), "rag_retrieval_log", ["user_id"])
    op.create_index(op.f("ix_rag_retrieval_log_knowledge_base_id"), "rag_retrieval_log", ["knowledge_base_id"])
    op.create_table(
        "knowledge_task",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_key", sa.String(128), nullable=False, unique=True),
        sa.Column("task_type", sa.String(32), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("knowledge_document.id"), nullable=False),
        sa.Column("knowledge_base_id", sa.Integer(), sa.ForeignKey("knowledge_base.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id")),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error_message", sa.Text()),
        *timestamps(),
    )
    for column in ("document_id", "knowledge_base_id", "user_id", "status"):
        op.create_index(op.f(f"ix_knowledge_task_{column}"), "knowledge_task", [column])


def downgrade() -> None:
    for table in (
        "knowledge_task", "rag_retrieval_log", "knowledge_chunk",
        "knowledge_document", "knowledge_base",
    ):
        op.drop_table(table)
