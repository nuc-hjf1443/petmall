from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.coin import CoinTask, CoinTaskRecord, DailyCheckin, PetCoinAccount, PetCoinLog


async def get_coin_account(db: AsyncSession, user_id: int, *, lock: bool = False) -> PetCoinAccount | None:
    statement = select(PetCoinAccount).where(PetCoinAccount.user_id == user_id)
    if lock:
        statement = statement.with_for_update()
    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def get_coin_log_by_key(db: AsyncSession, idempotency_key: str) -> PetCoinLog | None:
    result = await db.execute(
        select(PetCoinLog).where(PetCoinLog.idempotency_key == idempotency_key)
    )
    return result.scalar_one_or_none()


async def list_coin_logs(db: AsyncSession, user_id: int, *, offset: int = 0, limit: int = 50) -> list[PetCoinLog]:
    result = await db.execute(
        select(PetCoinLog)
        .where(PetCoinLog.user_id == user_id)
        .order_by(PetCoinLog.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_checkin(db: AsyncSession, user_id: int, checkin_date) -> DailyCheckin | None:
    result = await db.execute(
        select(DailyCheckin).where(
            DailyCheckin.user_id == user_id,
            DailyCheckin.checkin_date == checkin_date,
        )
    )
    return result.scalar_one_or_none()


async def list_enabled_tasks(db: AsyncSession) -> list[CoinTask]:
    result = await db.execute(
        select(CoinTask)
        .where(CoinTask.is_enabled.is_(True))
        .order_by(CoinTask.id.asc())
    )
    return list(result.scalars().all())


async def get_task(db: AsyncSession, task_id: int) -> CoinTask | None:
    result = await db.execute(
        select(CoinTask).where(CoinTask.id == task_id, CoinTask.is_enabled.is_(True))
    )
    return result.scalar_one_or_none()


async def list_task_records(db: AsyncSession, user_id: int) -> list[CoinTaskRecord]:
    result = await db.execute(select(CoinTaskRecord).where(CoinTaskRecord.user_id == user_id))
    return list(result.scalars().all())


async def get_task_record(db: AsyncSession, user_id: int, task_id: int) -> CoinTaskRecord | None:
    result = await db.execute(
        select(CoinTaskRecord).where(
            CoinTaskRecord.user_id == user_id,
            CoinTaskRecord.task_id == task_id,
        )
    )
    return result.scalar_one_or_none()
