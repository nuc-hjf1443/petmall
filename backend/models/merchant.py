from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class Merchant(Base, TimestampMixin):
    __tablename__ = "merchant"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), unique=True, index=True, nullable=False)
    shop_name: Mapped[str] = mapped_column(String(128), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(64), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    business_scope: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str | None] = mapped_column(String(64), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True, nullable=False)
    audit_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    qualifications: Mapped[list["MerchantQualification"]] = relationship(
        back_populates="merchant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class MerchantQualification(Base, TimestampMixin):
    __tablename__ = "merchant_qualification"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchant.id"), index=True, nullable=False)
    qualification_type: Mapped[str] = mapped_column(String(64), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    merchant: Mapped[Merchant] = relationship(back_populates="qualifications")


class MerchantStaff(Base, TimestampMixin):
    __tablename__ = "merchant_staff"
    __table_args__ = (
        UniqueConstraint("merchant_id", "user_id", name="uq_merchant_staff_merchant_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchant.id"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="owner", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class MerchantFollow(Base, TimestampMixin):
    __tablename__ = "merchant_follow"
    __table_args__ = (
        UniqueConstraint("user_id", "merchant_id", name="uq_merchant_follow_user_merchant"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchant.id"), index=True, nullable=False)
