from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_db, require_admin
from models.user import User
from schemas.wallet_schema import (
    AdminWithdrawalListResponse,
    WalletAccountResponse,
    WalletRechargeCreate,
    WalletRechargePaymentResponse,
    WalletTransactionResponse,
    WithdrawalCreate,
    WithdrawalResponse,
    WithdrawalReviewRequest,
)
from services.wallet_service import (
    approve_withdrawal,
    create_wallet_recharge_payment,
    create_withdrawal,
    get_admin_withdrawals,
    get_my_withdrawals,
    get_wallet_logs,
    get_wallet_overview,
    reject_withdrawal,
)


router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("/me", response_model=WalletAccountResponse)
async def my_wallet(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await get_wallet_overview(db, user.id)


@router.get("/transactions", response_model=list[WalletTransactionResponse])
async def my_wallet_transactions(
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_wallet_logs(db, user.id, limit=limit)


@router.post("/recharges", response_model=WalletRechargePaymentResponse)
async def recharge_wallet(
    payload: WalletRechargeCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_wallet_recharge_payment(db, user.id, payload.amount, payload.payment_mode)


@router.post("/withdrawals", response_model=WithdrawalResponse)
async def request_withdrawal(
    payload: WithdrawalCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_withdrawal(
        db,
        user.id,
        amount=payload.amount,
        account_name=payload.account_name,
        alipay_account=payload.alipay_account,
    )


@router.get("/withdrawals", response_model=list[WithdrawalResponse])
async def my_withdrawals(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await get_my_withdrawals(db, user.id)


@router.get("/admin/withdrawals", response_model=AdminWithdrawalListResponse)
async def admin_withdrawals(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    keyword: str | None = None,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_admin_withdrawals(db, page=page, page_size=page_size, status=status, keyword=keyword)


@router.post("/admin/withdrawals/{withdrawal_id}/approve", response_model=WithdrawalResponse)
async def admin_approve_withdrawal(
    withdrawal_id: int,
    payload: WithdrawalReviewRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await approve_withdrawal(db, admin.id, withdrawal_id, payload.reason)


@router.post("/admin/withdrawals/{withdrawal_id}/reject", response_model=WithdrawalResponse)
async def admin_reject_withdrawal(
    withdrawal_id: int,
    payload: WithdrawalReviewRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await reject_withdrawal(db, admin.id, withdrawal_id, payload.reason)
