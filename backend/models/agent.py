from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class AgentSession(Base, TimestampMixin):
    __tablename__ = "agent_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    agent_type: Mapped[str] = mapped_column(String(32), default="qa", index=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pet_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    messages: Mapped[list["AgentMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    recommendations: Mapped[list["AgentRecommendation"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AgentMessage(Base, TimestampMixin):
    __tablename__ = "agent_message"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("agent_session.id"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), default="normal", nullable=False)
    references: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped[AgentSession] = relationship(back_populates="messages")
    recommendations: Mapped[list["AgentRecommendation"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AgentRecommendation(Base, TimestampMixin):
    __tablename__ = "agent_recommendation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("agent_session.id"), index=True, nullable=False)
    message_id: Mapped[int] = mapped_column(ForeignKey("agent_message.id"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True, nullable=False)
    sku_id: Mapped[int | None] = mapped_column(ForeignKey("product_sku.id"), index=True, nullable=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    caution: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="product_search", nullable=False)

    session: Mapped[AgentSession] = relationship(back_populates="recommendations")
    message: Mapped[AgentMessage] = relationship(back_populates="recommendations")
