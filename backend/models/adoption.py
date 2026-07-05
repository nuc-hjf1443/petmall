from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class AdoptionPet(Base, TimestampMixin):
    __tablename__ = "adoption_pet"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    publisher_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    species: Mapped[str] = mapped_column(String(32), nullable=False)
    breed: Mapped[str | None] = mapped_column(String(64), nullable=True)
    age_text: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    city: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    health_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_image: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="published", index=True, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)

    applications: Mapped[list["AdoptionApplication"]] = relationship(
        back_populates="adoption_pet",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AdoptionApplication(Base, TimestampMixin):
    __tablename__ = "adoption_application"
    __table_args__ = (
        UniqueConstraint("adoption_pet_id", "applicant_id", name="uq_adoption_application_pet_applicant"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    adoption_pet_id: Mapped[int] = mapped_column(ForeignKey("adoption_pet.id"), index=True, nullable=False)
    applicant_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    contact_name: Mapped[str] = mapped_column(String(64), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    living_city: Mapped[str] = mapped_column(String(64), nullable=False)
    living_condition: Mapped[str] = mapped_column(String(128), nullable=False)
    experience: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True, nullable=False)
    audit_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    audited_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    audited_at: Mapped[str | None] = mapped_column(String(64), nullable=True)

    adoption_pet: Mapped[AdoptionPet] = relationship(back_populates="applications")


class AdoptionFollowUp(Base, TimestampMixin):
    __tablename__ = "adoption_follow_up"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("adoption_application.id"), index=True, nullable=False)
    operator_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str | None] = mapped_column(String(64), nullable=True)
