from datetime import UTC, date, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import bad_request, conflict, not_found
from models.coin import CoinLogType, CoinTask, CoinTaskRecord, DailyCheckin, PetCoinAccount, PetCoinLog
from models.database import AsyncSessionLocal
from repository.coin_repository import (
    get_checkin,
    get_coin_account,
    get_coin_log_by_key,
    get_task,
    get_task_record,
    list_coin_logs,
    list_enabled_tasks,
    list_task_records,
)


CHECKIN_REWARD = 10
DEFAULT_TASKS = (
    ("complete_pet_profile", "完善宠物档案", 20, "profile", "完善一只宠物的基础档案"),
    ("complete_pet_detail", "完善宠物详细资料", 30, "profile", "完善宠物健康、饮食和用品偏好"),
)


async def _flush_idempotent_change(db: AsyncSession, idempotency_key: str | None) -> None:
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        if idempotency_key and await get_coin_log_by_key(db, idempotency_key):
            return
        raise


async def get_or_create_account(db: AsyncSession, user_id: int, *, lock: bool = False) -> PetCoinAccount:
    account = await get_coin_account(db, user_id, lock=lock)
    if account is not None:
        return account
    account = PetCoinAccount(user_id=user_id)
    db.add(account)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        account = await get_coin_account(db, user_id, lock=lock)
        if account is None:
            raise
    return account


async def get_account(db: AsyncSession, user_id: int) -> PetCoinAccount:
    account = await get_or_create_account(db, user_id)
    await db.commit()
    await db.refresh(account)
    return account


async def get_logs(db: AsyncSession, user_id: int, page: int = 1, page_size: int = 50) -> list[PetCoinLog]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    return await list_coin_logs(db, user_id, offset=(page - 1) * page_size, limit=page_size)


async def _write_log(
    db: AsyncSession,
    account: PetCoinAccount,
    *,
    change_amount: int,
    balance_before: int,
    frozen_before: int,
    log_type: str,
    source: str,
    related_id: int | None,
    idempotency_key: str | None,
    remark: str | None = None,
) -> None:
    db.add(
        PetCoinLog(
            user_id=account.user_id,
            change_amount=change_amount,
            balance_before=balance_before,
            balance_after=account.balance,
            frozen_before=frozen_before,
            frozen_after=account.frozen_balance,
            type=log_type,
            source=source,
            related_id=related_id,
            idempotency_key=idempotency_key,
            remark=remark,
        )
    )


async def grant_coin(
    db: AsyncSession,
    user_id: int,
    amount: int,
    source: str,
    related_id: int | None = None,
    idempotency_key: str | None = None,
) -> None:
    if amount <= 0:
        raise bad_request("Coin amount must be positive")
    if idempotency_key and await get_coin_log_by_key(db, idempotency_key):
        return
    account = await get_or_create_account(db, user_id, lock=True)
    balance_before = account.balance
    frozen_before = account.frozen_balance
    account.balance += amount
    account.total_earned += amount
    log_type = CoinLogType.ORDER_REWARD.value if source == "order_reward" else CoinLogType.GRANT.value
    await _write_log(
        db,
        account,
        change_amount=amount,
        balance_before=balance_before,
        frozen_before=frozen_before,
        log_type=log_type,
        source=source,
        related_id=related_id,
        idempotency_key=idempotency_key,
    )
    await _flush_idempotent_change(db, idempotency_key)


async def freeze_coin(
    db: AsyncSession,
    user_id: int,
    amount: int,
    source: str,
    related_id: int | None = None,
    idempotency_key: str | None = None,
) -> None:
    if amount <= 0:
        raise bad_request("Coin amount must be positive")
    if idempotency_key and await get_coin_log_by_key(db, idempotency_key):
        return
    account = await get_or_create_account(db, user_id, lock=True)
    if account.balance < amount:
        raise conflict("Insufficient coin balance")
    balance_before = account.balance
    frozen_before = account.frozen_balance
    account.balance -= amount
    account.frozen_balance += amount
    await _write_log(
        db,
        account,
        change_amount=-amount,
        balance_before=balance_before,
        frozen_before=frozen_before,
        log_type=CoinLogType.FREEZE.value,
        source=source,
        related_id=related_id,
        idempotency_key=idempotency_key,
    )
    await _flush_idempotent_change(db, idempotency_key)


async def deduct_coin(
    db: AsyncSession,
    user_id: int,
    amount: int,
    source: str,
    related_id: int | None = None,
    idempotency_key: str | None = None,
) -> None:
    if amount <= 0:
        raise bad_request("Coin amount must be positive")
    if idempotency_key and await get_coin_log_by_key(db, idempotency_key):
        return
    account = await get_or_create_account(db, user_id, lock=True)
    if account.balance < amount:
        raise conflict("Insufficient coin balance")
    balance_before = account.balance
    frozen_before = account.frozen_balance
    account.balance -= amount
    account.total_spent += amount
    await _write_log(
        db,
        account,
        change_amount=-amount,
        balance_before=balance_before,
        frozen_before=frozen_before,
        log_type=CoinLogType.DEDUCT.value,
        source=source,
        related_id=related_id,
        idempotency_key=idempotency_key,
    )
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()


async def checkin(db: AsyncSession, user_id: int) -> tuple[DailyCheckin, PetCoinAccount]:
    today = datetime.now(UTC).date()
    if await get_checkin(db, user_id, today):
        raise conflict("Already checked in today")
    record = DailyCheckin(user_id=user_id, checkin_date=today, reward_amount=CHECKIN_REWARD)
    db.add(record)
    await grant_coin(
        db,
        user_id,
        CHECKIN_REWARD,
        source="checkin",
        related_id=None,
        idempotency_key=f"checkin:{user_id}:{today.isoformat()}",
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise conflict("Already checked in today")
    account = await get_or_create_account(db, user_id)
    return record, account


async def ensure_default_tasks(db: AsyncSession) -> None:
    existing = await list_enabled_tasks(db)
    existing_codes = {task.code for task in existing}
    for code, name, reward, task_type, description in DEFAULT_TASKS:
        if code not in existing_codes:
            db.add(
                CoinTask(
                    code=code,
                    name=name,
                    reward_amount=reward,
                    task_type=task_type,
                    description=description,
                )
            )
    await db.flush()


async def get_tasks(db: AsyncSession, user_id: int) -> list[tuple[CoinTask, bool]]:
    await ensure_default_tasks(db)
    tasks = await list_enabled_tasks(db)
    records = await list_task_records(db, user_id)
    claimed = {record.task_id for record in records}
    await db.commit()
    return [(task, task.id in claimed) for task in tasks]


async def claim_task(db: AsyncSession, user_id: int, task_id: int) -> tuple[int, PetCoinAccount]:
    await ensure_default_tasks(db)
    task = await get_task(db, task_id)
    if task is None:
        raise not_found("Coin task not found")
    if await get_task_record(db, user_id, task_id):
        raise conflict("Coin task already claimed")
    record = CoinTaskRecord(
        user_id=user_id,
        task_id=task.id,
        reward_amount=task.reward_amount,
    )
    db.add(record)
    await grant_coin(
        db,
        user_id,
        task.reward_amount,
        source="task",
        related_id=task.id,
        idempotency_key=f"task:{user_id}:{task.id}",
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise conflict("Coin task already claimed")
    account = await get_or_create_account(db, user_id)
    return task.reward_amount, account


class RealCoinRewardAdapter:
    async def grant_order_reward(
        self, *, user_id: int, order_id: int, pay_amount: int, idempotency_key: str
    ) -> None:
        reward = pay_amount // 100
        if reward <= 0:
            return
        async with AsyncSessionLocal() as db:
            await grant_coin(
                db,
                user_id,
                reward,
                source="order_reward",
                related_id=order_id,
                idempotency_key=idempotency_key,
            )
            await db.commit()
