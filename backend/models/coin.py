from datetime import date
from enum import StrEnum

from sqlalchemy import Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class CoinLogType(StrEnum):
    GRANT = "grant"
    FREEZE = "freeze"
    DEDUCT = "deduct"
    CHECKIN = "checkin"
    TASK = "task"
    ORDER_REWARD = "order_reward"


class PetCoinAccount(Base, TimestampMixin):
    __tablename__ = "pet_coin_account"
    __table_args__ = (UniqueConstraint("user_id", name="uq_pet_coin_account_user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    frozen_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_spent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class PetCoinLog(Base, TimestampMixin):
    __tablename__ = "pet_coin_log"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_pet_coin_log_idempotency_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    change_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_before: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    frozen_before: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    frozen_after: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    related_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)


class CoinTask(Base, TimestampMixin):
    __tablename__ = "coin_task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    reward_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class CoinTaskRecord(Base, TimestampMixin):
    __tablename__ = "coin_task_record"
    __table_args__ = (UniqueConstraint("user_id", "task_id", name="uq_coin_task_record_user_task"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    task_id: Mapped[int] = mapped_column(ForeignKey("coin_task.id"), index=True, nullable=False)
    reward_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="claimed", nullable=False)


class DailyCheckin(Base, TimestampMixin):
    __tablename__ = "daily_checkin"
    __table_args__ = (UniqueConstraint("user_id", "checkin_date", name="uq_daily_checkin_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    checkin_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    reward_amount: Mapped[int] = mapped_column(Integer, nullable=False)
