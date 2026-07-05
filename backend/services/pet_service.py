from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import not_found
from models.pet import PetDetailProfile, PetGrowthRecord, PetHealthReminder, PetProfile
from repository.pet_repository import (
    get_growth_record,
    get_pet_detail_profile,
    get_reminder,
    get_user_pet,
    list_growth_records,
    list_reminders,
    list_user_pets,
)
from schemas.pet_schema import (
    PetDetailProfileUpdate,
    PetGrowthRecordCreate,
    PetHealthReminderCreate,
    PetHealthReminderUpdate,
    PetProfileCreate,
    PetProfileUpdate,
)
from services.profile_document_service import calculate_profile_completeness, build_pet_profile_document


async def list_pets(db: AsyncSession, user_id: int) -> list[PetProfile]:
    return await list_user_pets(db, user_id)


async def create_pet(db: AsyncSession, user_id: int, payload: PetProfileCreate) -> PetProfile:
    pet = PetProfile(user_id=user_id, **payload.model_dump())
    db.add(pet)
    await db.commit()
    await db.refresh(pet)
    return pet


async def get_pet(db: AsyncSession, user_id: int, pet_id: int) -> PetProfile:
    pet = await get_user_pet(db, user_id, pet_id)
    if pet is None:
        raise not_found("Pet not found")
    return pet


async def update_pet(db: AsyncSession, user_id: int, pet_id: int, payload: PetProfileUpdate) -> PetProfile:
    pet = await get_pet(db, user_id, pet_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(pet, field, value)
    await db.commit()
    await db.refresh(pet)
    return pet


async def delete_pet(db: AsyncSession, user_id: int, pet_id: int) -> None:
    pet = await get_pet(db, user_id, pet_id)
    pet.is_deleted = True
    await db.commit()


async def create_growth_record(
    db: AsyncSession, user_id: int, pet_id: int, payload: PetGrowthRecordCreate
) -> PetGrowthRecord:
    await get_pet(db, user_id, pet_id)
    record = PetGrowthRecord(user_id=user_id, pet_id=pet_id, **payload.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_growth_records(db: AsyncSession, user_id: int, pet_id: int) -> list[PetGrowthRecord]:
    await get_pet(db, user_id, pet_id)
    return await list_growth_records(db, user_id, pet_id)


async def delete_growth_record(db: AsyncSession, user_id: int, pet_id: int, record_id: int) -> None:
    await get_pet(db, user_id, pet_id)
    record = await get_growth_record(db, user_id, pet_id, record_id)
    if record is None:
        raise not_found("Growth record not found")
    await db.delete(record)
    await db.commit()


async def get_detail_profile(db: AsyncSession, user_id: int, pet_id: int) -> PetDetailProfile:
    await get_pet(db, user_id, pet_id)
    detail = await get_pet_detail_profile(db, user_id, pet_id)
    if detail is None:
        detail = PetDetailProfile(user_id=user_id, pet_id=pet_id)
        detail.profile_completeness = calculate_profile_completeness(await get_pet(db, user_id, pet_id), detail)["completeness"]
        db.add(detail)
        await db.commit()
        await db.refresh(detail)
    return detail


async def update_detail_profile(
    db: AsyncSession, user_id: int, pet_id: int, payload: PetDetailProfileUpdate
) -> PetDetailProfile:
    pet = await get_pet(db, user_id, pet_id)
    detail = await get_pet_detail_profile(db, user_id, pet_id)
    if detail is None:
        detail = PetDetailProfile(user_id=user_id, pet_id=pet_id)
        db.add(detail)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(detail, field, value)
    detail.profile_completeness = calculate_profile_completeness(pet, detail)["completeness"]
    await db.commit()
    await db.refresh(detail)
    return detail


async def get_profile_completeness(db: AsyncSession, user_id: int, pet_id: int) -> dict:
    pet = await get_pet(db, user_id, pet_id)
    detail = await get_pet_detail_profile(db, user_id, pet_id)
    return calculate_profile_completeness(pet, detail)


async def preview_profile_document(db: AsyncSession, user_id: int, pet_id: int) -> dict:
    return await build_pet_profile_document(db, user_id, pet_id)


async def create_reminder(
    db: AsyncSession, user_id: int, pet_id: int, payload: PetHealthReminderCreate
) -> PetHealthReminder:
    await get_pet(db, user_id, pet_id)
    reminder = PetHealthReminder(user_id=user_id, pet_id=pet_id, **payload.model_dump())
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return reminder


async def get_reminders(db: AsyncSession, user_id: int, pet_id: int) -> list[PetHealthReminder]:
    await get_pet(db, user_id, pet_id)
    return await list_reminders(db, user_id, pet_id)


async def update_reminder(
    db: AsyncSession, user_id: int, pet_id: int, reminder_id: int, payload: PetHealthReminderUpdate
) -> PetHealthReminder:
    await get_pet(db, user_id, pet_id)
    reminder = await get_reminder(db, user_id, pet_id, reminder_id)
    if reminder is None:
        raise not_found("Reminder not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(reminder, field, value)
    await db.commit()
    await db.refresh(reminder)
    return reminder


async def delete_reminder(db: AsyncSession, user_id: int, pet_id: int, reminder_id: int) -> None:
    await get_pet(db, user_id, pet_id)
    reminder = await get_reminder(db, user_id, pet_id, reminder_id)
    if reminder is None:
        raise not_found("Reminder not found")
    await db.delete(reminder)
    await db.commit()
