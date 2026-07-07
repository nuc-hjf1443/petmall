from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class WalletTransactionType(StrEnum):
    RECHARGE = "recharge"
    FREEZE_WITHDRAWAL = "freeze_withdrawal"
    WITHDRAWAL_PAID = "withdrawal_paid"
    WITHDRAWAL_REJECTED = "withdrawal_rejected"


class WithdrawalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class WalletAccount(Base, TimestampMixin):
    __tablename__ = "wallet_account"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_wallet_account_user_id"),
        CheckConstraint("balance >= 0 AND frozen_balance >= 0", name="ck_wallet_account_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    frozen_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_recharged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_withdrawn: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class WalletTransaction(Base, TimestampMixin):
    __tablename__ = "wallet_transaction"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_wallet_transaction_idempotency_key"),
        CheckConstraint("balance_before >= 0 AND balance_after >= 0", name="ck_wallet_transaction_balance_non_negative"),
        CheckConstraint("frozen_before >= 0 AND frozen_after >= 0", name="ck_wallet_transaction_frozen_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    change_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_before: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    frozen_before: Mapped[int] = mapped_column(Integer, nullable=False)
    frozen_after: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    related_id: Mapped[int | None] = mapped_column(Integer, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    remark: Mapped[str | None] = mapped_column(Text)


class WalletRecharge(Base, TimestampMixin):
    __tablename__ = "wallet_recharge"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_wallet_recharge_amount_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recharge_no: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WithdrawalRequest(Base, TimestampMixin):
    __tablename__ = "withdrawal_request"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_withdrawal_request_amount_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    withdrawal_no: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    account_name: Mapped[str] = mapped_column(String(64), nullable=False)
    alipay_account: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=WithdrawalStatus.PENDING.value, index=True, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
