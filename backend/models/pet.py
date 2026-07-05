from datetime import date, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class PetReminderStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    CANCELLED = "cancelled"


class PetProfile(Base, TimestampMixin):
    __tablename__ = "pet_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    pet_type: Mapped[str] = mapped_column(String(32), nullable=False)
    breed: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    birthday: Mapped[date | None] = mapped_column(Date, nullable=True)
    arrival_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sterilized: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    vaccine_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    deworm_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    detail_profile: Mapped["PetDetailProfile | None"] = relationship(
        back_populates="pet",
        cascade="all, delete-orphan",
        lazy="selectin",
        uselist=False,
    )
    growth_records: Mapped[list["PetGrowthRecord"]] = relationship(
        back_populates="pet",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    reminders: Mapped[list["PetHealthReminder"]] = relationship(
        back_populates="pet",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PetGrowthRecord(Base, TimestampMixin):
    __tablename__ = "pet_growth_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pet_profile.id"), index=True, nullable=False)
    record_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_urls: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    happened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pet: Mapped[PetProfile] = relationship(back_populates="growth_records")


class PetHealthReminder(Base, TimestampMixin):
    __tablename__ = "pet_health_reminder"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pet_profile.id"), index=True, nullable=False)
    reminder_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    repeat_rule: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=PetReminderStatus.PENDING.value, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    pet: Mapped[PetProfile] = relationship(back_populates="reminders")


class PetAlbum(Base, TimestampMixin):
    __tablename__ = "pet_album"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pet_profile.id"), index=True, nullable=False)
    media_url: Mapped[str] = mapped_column(String(512), nullable=False)
    media_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class PetDetailProfile(Base, TimestampMixin):
    __tablename__ = "pet_detail_profile"
    __table_args__ = (UniqueConstraint("pet_id", name="uq_pet_detail_profile_pet_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pet_profile.id"), index=True, nullable=False)
    body_size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    health_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    allergy_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    diet_preference: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_preference: Mapped[str | None] = mapped_column(Text, nullable=True)
    behavior_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    care_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_completeness: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    pet: Mapped[PetProfile] = relationship(back_populates="detail_profile")


class PetProfileDocument(Base, TimestampMixin):
    __tablename__ = "pet_profile_document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pet_profile.id"), index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    profile_completeness: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
