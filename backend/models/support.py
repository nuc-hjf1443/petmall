from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, utc_now


class SupportConversationType(StrEnum):
    PLATFORM = "platform"
    MERCHANT = "merchant"
    ADOPTION = "adoption"


class SupportConversationStatus(StrEnum):
    PENDING = "pending"
    RESOLVED = "resolved"


class SupportConversation(Base, TimestampMixin):
    __tablename__ = "support_conversation"
    __table_args__ = (
        CheckConstraint(
            "type IN ('platform', 'merchant', 'adoption')",
            name="ck_support_conversation_type_valid",
        ),
        CheckConstraint(
            "status IN ('pending', 'resolved')",
            name="ck_support_conversation_status_valid",
        ),
        Index("ix_support_conversation_user_type", "user_id", "type"),
        Index("ix_support_conversation_merchant_status", "merchant_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default=SupportConversationStatus.PENDING.value,
        index=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    merchant_id: Mapped[int | None] = mapped_column(ForeignKey("merchant.id"), index=True, nullable=True)
    adoption_pet_id: Mapped[int | None] = mapped_column(ForeignKey("adoption_pet.id"), index=True, nullable=True)
    adoption_application_id: Mapped[int | None] = mapped_column(
        ForeignKey("adoption_application.id"),
        index=True,
        nullable=True,
    )
    assigned_to_platform: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    messages: Mapped[list["SupportMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SupportMessage.created_at, SupportMessage.id",
    )


class SupportMessage(Base, TimestampMixin):
    __tablename__ = "support_message"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("support_conversation.id"),
        index=True,
        nullable=False,
    )
    sender_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    conversation: Mapped[SupportConversation] = relationship(back_populates="messages")
