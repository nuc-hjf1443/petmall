from enum import StrEnum
from typing import Any

from sqlalchemy import ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class DocumentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PARSED = "parsed"
    FAILED = "failed"
    DELETING = "deleting"


class KnowledgeBase(Base, TimestampMixin):
    __tablename__ = "knowledge_base"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    scope: Mapped[str] = mapped_column(String(16), default="private", index=True)


class KnowledgeDocument(Base, TimestampMixin):
    __tablename__ = "knowledge_document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    knowledge_base_id: Mapped[int] = mapped_column(ForeignKey("knowledge_base.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(16))
    file_path: Mapped[str] = mapped_column(String(512))
    source_type: Mapped[str] = mapped_column(String(32), default="upload")
    pet_id: Mapped[int | None] = mapped_column(Integer, index=True)
    source_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    parse_status: Mapped[str] = mapped_column(String(32), default=DocumentStatus.PENDING.value, index=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    index_version: Mapped[int] = mapped_column(Integer, default=1)
    error_message: Mapped[str | None] = mapped_column(Text)


class KnowledgeChunk(Base, TimestampMixin):
    __tablename__ = "knowledge_chunk"
    __table_args__ = (
        UniqueConstraint("document_id", "index_version", "chunk_index", name="uq_document_chunk_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    knowledge_base_id: Mapped[int] = mapped_column(ForeignKey("knowledge_base.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("knowledge_document.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), index=True)
    index_version: Mapped[int] = mapped_column(Integer)
    chunk_index: Mapped[int] = mapped_column(Integer)
    vector_id: Mapped[str] = mapped_column(String(128), unique=True)
    content: Mapped[str] = mapped_column(Text)


class RagRetrievalLog(Base, TimestampMixin):
    __tablename__ = "rag_retrieval_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), index=True)
    knowledge_base_id: Mapped[int | None] = mapped_column(Integer, index=True)
    query_text: Mapped[str] = mapped_column(String(500))
    results: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    caller: Mapped[str] = mapped_column(String(64), default="service")


class KnowledgeTask(Base, TimestampMixin):
    __tablename__ = "knowledge_task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_key: Mapped[str] = mapped_column(String(128), unique=True)
    task_type: Mapped[str] = mapped_column(String(32))
    document_id: Mapped[int] = mapped_column(ForeignKey("knowledge_document.id"), index=True)
    knowledge_base_id: Mapped[int] = mapped_column(ForeignKey("knowledge_base.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
