from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.pet import PetDetailProfile, PetGrowthRecord, PetHealthReminder, PetProfile


async def list_user_pets(db: AsyncSession, user_id: int) -> list[PetProfile]:
    result = await db.execute(
        select(PetProfile)
        .options(selectinload(PetProfile.detail_profile))
        .where(PetProfile.user_id == user_id, PetProfile.is_deleted.is_(False))
        .order_by(PetProfile.updated_at.desc(), PetProfile.id.desc())
    )
    return list(result.scalars().all())


async def get_user_pet(db: AsyncSession, user_id: int, pet_id: int, *, lock: bool = False) -> PetProfile | None:
    statement = (
        select(PetProfile)
        .options(
            selectinload(PetProfile.detail_profile),
            selectinload(PetProfile.growth_records),
            selectinload(PetProfile.reminders),
        )
        .where(
            PetProfile.id == pet_id,
            PetProfile.user_id == user_id,
            PetProfile.is_deleted.is_(False),
        )
    )
    if lock:
        statement = statement.with_for_update()
    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def get_pet_detail_profile(db: AsyncSession, user_id: int, pet_id: int) -> PetDetailProfile | None:
    result = await db.execute(
        select(PetDetailProfile).where(
            PetDetailProfile.user_id == user_id,
            PetDetailProfile.pet_id == pet_id,
        )
    )
    return result.scalar_one_or_none()


async def get_growth_record(
    db: AsyncSession, user_id: int, pet_id: int, record_id: int
) -> PetGrowthRecord | None:
    result = await db.execute(
        select(PetGrowthRecord).where(
            PetGrowthRecord.id == record_id,
            PetGrowthRecord.user_id == user_id,
            PetGrowthRecord.pet_id == pet_id,
        )
    )
    return result.scalar_one_or_none()


async def list_growth_records(db: AsyncSession, user_id: int, pet_id: int) -> list[PetGrowthRecord]:
    result = await db.execute(
        select(PetGrowthRecord)
        .where(PetGrowthRecord.user_id == user_id, PetGrowthRecord.pet_id == pet_id)
        .order_by(PetGrowthRecord.happened_at.desc(), PetGrowthRecord.id.desc())
    )
    return list(result.scalars().all())


async def get_reminder(
    db: AsyncSession, user_id: int, pet_id: int, reminder_id: int
) -> PetHealthReminder | None:
    result = await db.execute(
        select(PetHealthReminder).where(
            PetHealthReminder.id == reminder_id,
            PetHealthReminder.user_id == user_id,
            PetHealthReminder.pet_id == pet_id,
        )
    )
    return result.scalar_one_or_none()


async def list_reminders(db: AsyncSession, user_id: int, pet_id: int) -> list[PetHealthReminder]:
    result = await db.execute(
        select(PetHealthReminder)
        .where(PetHealthReminder.user_id == user_id, PetHealthReminder.pet_id == pet_id)
        .order_by(PetHealthReminder.due_at.asc(), PetHealthReminder.id.asc())
    )
    return list(result.scalars().all())
