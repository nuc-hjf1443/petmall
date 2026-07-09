from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import bad_request, conflict, not_found
from models.base import utc_now
from models.order import PaymentStatus, PaymentTransaction
from models.wallet import (
    WalletRecharge,
    WalletTransaction,
    WalletTransactionType,
    WithdrawalRequest,
    WithdrawalStatus,
)
from repository.wallet_repository import (
    get_or_create_wallet_account,
    get_wallet_recharge,
    get_withdrawal,
    list_admin_withdrawals,
    list_user_withdrawals,
    list_wallet_transactions,
)
from schemas.order_schema import PaymentResponse
from schemas.wallet_schema import AdminWithdrawalListResponse, WalletRechargePaymentResponse
from settings.config import get_settings


def _serial(prefix: str) -> str:
    return f"{prefix}{utc_now():%Y%m%d%H%M%S}{uuid4().hex[:10].upper()}"


def _payment_response(payment: PaymentTransaction, pay_url: str | None = None) -> PaymentResponse:
    return PaymentResponse(
        out_trade_no=payment.out_trade_no,
        order_id=payment.business_id,
        business_type=payment.business_type,
        amount=payment.amount,
        status=payment.status,
        payment_mode=payment.payment_mode,
        pay_url=pay_url,
        channel_trade_no=payment.channel_trade_no,
    )


async def get_wallet_overview(db: AsyncSession, user_id: int):
    return await get_or_create_wallet_account(db, user_id)


async def get_wallet_logs(db: AsyncSession, user_id: int, limit: int = 20):
    return await list_wallet_transactions(db, user_id, limit=limit)


async def create_wallet_recharge_payment(
    db: AsyncSession,
    user_id: int,
    amount: int,
    payment_mode: str,
) -> WalletRechargePaymentResponse:
    settings = get_settings()
    if payment_mode not in {"mock", "alipay_sandbox"}:
        raise conflict("Unsupported payment mode")
    if payment_mode == "mock" and not settings.mock_payment_enabled:
        raise conflict("Mock payment is disabled")

    recharge = WalletRecharge(
        recharge_no=_serial("WR"),
        user_id=user_id,
        amount=amount,
        status="pending",
    )
    db.add(recharge)
    await db.flush()
    payment = PaymentTransaction(
        out_trade_no=_serial("PAY"),
        business_type="wallet_recharge",
        business_id=recharge.id,
        pay_channel=payment_mode,
        payment_mode=payment_mode,
        amount=amount,
        status=PaymentStatus.CREATED.value,
    )
    db.add(payment)
    try:
        await db.commit()
        await db.refresh(recharge)
        await db.refresh(payment)
    except IntegrityError:
        await db.rollback()
        raise conflict("Recharge payment already exists")

    pay_url = None
    if payment_mode == "alipay_sandbox":
        from services.payment_service import build_alipay_page_url

        pay_url = build_alipay_page_url(payment)
    return WalletRechargePaymentResponse(
        recharge=recharge,
        payment=_payment_response(payment, pay_url),
    )


async def complete_wallet_recharge(
    db: AsyncSession,
    payment: PaymentTransaction,
    channel_trade_no: str,
    raw: dict,
) -> PaymentResponse:
    if payment.status == PaymentStatus.PAID.value:
        return _payment_response(payment)
    recharge = await get_wallet_recharge(db, payment.business_id, lock=True)
    if recharge is None:
        raise not_found("Recharge not found")
    if recharge.status == "paid":
        payment.status = PaymentStatus.PAID.value
        payment.channel_trade_no = channel_trade_no
        payment.paid_at = utc_now()
        await db.commit()
        return _payment_response(payment)

    account = await get_or_create_wallet_account(db, recharge.user_id, lock=True)
    before = account.balance
    frozen_before = account.frozen_balance
    account.balance += recharge.amount
    account.total_recharged += recharge.amount
    recharge.status = "paid"
    recharge.paid_at = utc_now()
    db.add(
        WalletTransaction(
            user_id=recharge.user_id,
            change_amount=recharge.amount,
            balance_before=before,
            balance_after=account.balance,
            frozen_before=frozen_before,
            frozen_after=account.frozen_balance,
            type=WalletTransactionType.RECHARGE.value,
            source="alipay_sandbox" if payment.payment_mode == "alipay_sandbox" else "mock",
            related_id=recharge.id,
            idempotency_key=f"wallet_recharge:{recharge.id}",
            remark="Wallet recharge paid",
        )
    )
    payment.status = PaymentStatus.PAID.value
    payment.channel_trade_no = channel_trade_no
    payment.raw_notify = raw
    payment.paid_at = utc_now()
    await db.commit()
    return _payment_response(payment)


async def ensure_payment_owner(db: AsyncSession, payment: PaymentTransaction, user_id: int) -> bool:
    if payment.business_type == "wallet_recharge":
        recharge = await get_wallet_recharge(db, payment.business_id)
        return recharge is not None and recharge.user_id == user_id
    return False


async def require_wallet_recharge_owner(db: AsyncSession, payment: PaymentTransaction, user_id: int) -> None:
    if payment.business_type != "wallet_recharge" or not await ensure_payment_owner(db, payment, user_id):
        raise not_found("Payment not found")


async def complete_mock_wallet_recharge(db: AsyncSession, payment: PaymentTransaction) -> PaymentResponse:
    if payment.payment_mode != "mock":
        raise conflict("Payment is not a mock wallet recharge")
    return await complete_wallet_recharge(db, payment, f"MOCK-{payment.out_trade_no}", {"source": "mock"})


async def create_withdrawal(
    db: AsyncSession,
    user_id: int,
    *,
    amount: int,
    account_name: str,
    alipay_account: str,
):
    account = await get_or_create_wallet_account(db, user_id, lock=True)
    if account.balance < amount:
        raise bad_request("Insufficient wallet balance")
    before = account.balance
    frozen_before = account.frozen_balance
    account.balance -= amount
    account.frozen_balance += amount
    withdrawal = WithdrawalRequest(
        withdrawal_no=_serial("WD"),
        user_id=user_id,
        amount=amount,
        account_name=account_name,
        alipay_account=alipay_account,
        status=WithdrawalStatus.PENDING.value,
    )
    db.add(withdrawal)
    await db.flush()
    db.add(
        WalletTransaction(
            user_id=user_id,
            change_amount=-amount,
            balance_before=before,
            balance_after=account.balance,
            frozen_before=frozen_before,
            frozen_after=account.frozen_balance,
            type=WalletTransactionType.FREEZE_WITHDRAWAL.value,
            source="withdrawal",
            related_id=withdrawal.id,
            idempotency_key=f"withdrawal:{withdrawal.id}:freeze",
            remark="Withdrawal request frozen",
        )
    )
    await db.commit()
    await db.refresh(withdrawal)
    return withdrawal


async def get_my_withdrawals(db: AsyncSession, user_id: int):
    return await list_user_withdrawals(db, user_id)


async def get_admin_withdrawals(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    status: str | None,
    keyword: str | None = None,
):
    items, total, page, page_size = await list_admin_withdrawals(
        db,
        page=page,
        page_size=page_size,
        status=status,
        keyword=keyword,
    )
    return AdminWithdrawalListResponse(items=items, total=total, page=page, page_size=page_size)


async def approve_withdrawal(db: AsyncSession, admin_id: int, withdrawal_id: int, reason: str | None):
    withdrawal = await get_withdrawal(db, withdrawal_id, lock=True)
    if withdrawal is None:
        raise not_found("Withdrawal not found")
    if withdrawal.status != WithdrawalStatus.PENDING.value:
        raise conflict("Withdrawal has been reviewed")
    account = await get_or_create_wallet_account(db, withdrawal.user_id, lock=True)
    if account.frozen_balance < withdrawal.amount:
        raise conflict("Frozen balance is insufficient")
    before = account.balance
    frozen_before = account.frozen_balance
    account.frozen_balance -= withdrawal.amount
    account.total_withdrawn += withdrawal.amount
    withdrawal.status = WithdrawalStatus.APPROVED.value
    withdrawal.reason = reason
    withdrawal.reviewed_by = admin_id
    withdrawal.reviewed_at = utc_now()
    db.add(
        WalletTransaction(
            user_id=withdrawal.user_id,
            change_amount=-withdrawal.amount,
            balance_before=before,
            balance_after=account.balance,
            frozen_before=frozen_before,
            frozen_after=account.frozen_balance,
            type=WalletTransactionType.WITHDRAWAL_PAID.value,
            source="mock_withdrawal",
            related_id=withdrawal.id,
            idempotency_key=f"withdrawal:{withdrawal.id}:approved",
            remark=reason or "Withdrawal approved with simulated payout",
        )
    )
    await db.commit()
    await db.refresh(withdrawal)
    return withdrawal


async def reject_withdrawal(db: AsyncSession, admin_id: int, withdrawal_id: int, reason: str | None):
    withdrawal = await get_withdrawal(db, withdrawal_id, lock=True)
    if withdrawal is None:
        raise not_found("Withdrawal not found")
    if withdrawal.status != WithdrawalStatus.PENDING.value:
        raise conflict("Withdrawal has been reviewed")
    account = await get_or_create_wallet_account(db, withdrawal.user_id, lock=True)
    if account.frozen_balance < withdrawal.amount:
        raise conflict("Frozen balance is insufficient")
    before = account.balance
    frozen_before = account.frozen_balance
    account.balance += withdrawal.amount
    account.frozen_balance -= withdrawal.amount
    withdrawal.status = WithdrawalStatus.REJECTED.value
    withdrawal.reason = reason
    withdrawal.reviewed_by = admin_id
    withdrawal.reviewed_at = utc_now()
    db.add(
        WalletTransaction(
            user_id=withdrawal.user_id,
            change_amount=withdrawal.amount,
            balance_before=before,
            balance_after=account.balance,
            frozen_before=frozen_before,
            frozen_after=account.frozen_balance,
            type=WalletTransactionType.WITHDRAWAL_REJECTED.value,
            source="withdrawal",
            related_id=withdrawal.id,
            idempotency_key=f"withdrawal:{withdrawal.id}:rejected",
            remark=reason or "Withdrawal rejected",
        )
    )
    await db.commit()
    await db.refresh(withdrawal)
    return withdrawal
