from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.wallet import WalletAccount, WalletRecharge, WalletTransaction, WithdrawalRequest


async def get_wallet_account(db: AsyncSession, user_id: int, lock: bool = False) -> WalletAccount | None:
    statement = select(WalletAccount).where(WalletAccount.user_id == user_id)
    if lock:
        statement = statement.with_for_update()
    return (await db.execute(statement)).scalar_one_or_none()


async def get_or_create_wallet_account(db: AsyncSession, user_id: int, lock: bool = False) -> WalletAccount:
    account = await get_wallet_account(db, user_id, lock=lock)
    if account is not None:
        return account
    account = WalletAccount(user_id=user_id, balance=0, frozen_balance=0, total_recharged=0, total_withdrawn=0)
    db.add(account)
    await db.flush()
    return account


async def get_wallet_recharge(db: AsyncSession, recharge_id: int, lock: bool = False) -> WalletRecharge | None:
    statement = select(WalletRecharge).where(WalletRecharge.id == recharge_id)
    if lock:
        statement = statement.with_for_update()
    return (await db.execute(statement)).scalar_one_or_none()


async def list_wallet_transactions(db: AsyncSession, user_id: int, limit: int = 20) -> list[WalletTransaction]:
    result = await db.execute(
        select(WalletTransaction)
        .where(WalletTransaction.user_id == user_id)
        .order_by(WalletTransaction.created_at.desc(), WalletTransaction.id.desc())
        .limit(min(max(limit, 1), 100))
    )
    return list(result.scalars().all())


async def list_user_withdrawals(db: AsyncSession, user_id: int) -> list[WithdrawalRequest]:
    result = await db.execute(
        select(WithdrawalRequest)
        .where(WithdrawalRequest.user_id == user_id)
        .order_by(WithdrawalRequest.created_at.desc(), WithdrawalRequest.id.desc())
    )
    return list(result.scalars().all())


async def get_withdrawal(db: AsyncSession, withdrawal_id: int, lock: bool = False) -> WithdrawalRequest | None:
    statement = select(WithdrawalRequest).where(WithdrawalRequest.id == withdrawal_id)
    if lock:
        statement = statement.with_for_update()
    return (await db.execute(statement)).scalar_one_or_none()


async def list_admin_withdrawals(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    status: str | None,
    keyword: str | None = None,
) -> tuple[list[WithdrawalRequest], int, int, int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    filters = []
    if status:
        filters.append(WithdrawalRequest.status == status)
    clean_keyword = keyword.strip() if keyword else ""
    if clean_keyword:
        pattern = f"%{clean_keyword}%"
        filters.append(
            or_(
                WithdrawalRequest.withdrawal_no.ilike(pattern),
                WithdrawalRequest.account_name.ilike(pattern),
                WithdrawalRequest.alipay_account.ilike(pattern),
                cast(WithdrawalRequest.user_id, String).ilike(pattern),
            )
        )
    total = int((await db.scalar(select(func.count(WithdrawalRequest.id)).where(*filters))) or 0)
    result = await db.execute(
        select(WithdrawalRequest)
        .where(*filters)
        .order_by(WithdrawalRequest.created_at.desc(), WithdrawalRequest.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total, page, page_size
