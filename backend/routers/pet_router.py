from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_db
from models.pet import PetDetailProfile, PetGrowthRecord, PetHealthReminder, PetProfile
from models.user import User
from schemas.pet_schema import (
    PetDetailProfileResponse,
    PetDetailProfileUpdate,
    PetGrowthRecordCreate,
    PetGrowthRecordResponse,
    PetHealthReminderCreate,
    PetHealthReminderResponse,
    PetHealthReminderUpdate,
    PetProfileCompletenessResponse,
    PetProfileCreate,
    PetProfileDocumentPreviewResponse,
    PetProfileResponse,
    PetProfileUpdate,
)
from services.pet_service import (
    create_growth_record,
    create_pet,
    create_reminder,
    delete_growth_record,
    delete_pet,
    delete_reminder,
    get_detail_profile,
    get_growth_records,
    get_pet,
    get_profile_completeness,
    get_reminders,
    list_pets,
    preview_profile_document,
    update_detail_profile,
    update_pet,
    update_reminder,
)


router = APIRouter(prefix="/pets", tags=["pets"])


@router.get("", response_model=list[PetProfileResponse])
async def get_my_pets(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PetProfile]:
    return await list_pets(db, user.id)


@router.post("", response_model=PetProfileResponse)
async def create_my_pet(
    payload: PetProfileCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PetProfile:
    return await create_pet(db, user.id, payload)


@router.get("/{pet_id}", response_model=PetProfileResponse)
async def get_my_pet(
    pet_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PetProfile:
    return await get_pet(db, user.id, pet_id)


@router.put("/{pet_id}", response_model=PetProfileResponse)
async def update_my_pet(
    pet_id: int,
    payload: PetProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PetProfile:
    return await update_pet(db, user.id, pet_id, payload)


@router.delete("/{pet_id}")
async def delete_my_pet(
    pet_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await delete_pet(db, user.id, pet_id)
    return {"message": "Pet deleted"}


@router.get("/{pet_id}/growth-records", response_model=list[PetGrowthRecordResponse])
async def list_my_pet_growth_records(
    pet_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PetGrowthRecord]:
    return await get_growth_records(db, user.id, pet_id)


@router.post("/{pet_id}/growth-records", response_model=PetGrowthRecordResponse)
async def create_my_pet_growth_record(
    pet_id: int,
    payload: PetGrowthRecordCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PetGrowthRecord:
    return await create_growth_record(db, user.id, pet_id, payload)


@router.delete("/{pet_id}/growth-records/{record_id}")
async def delete_my_pet_growth_record(
    pet_id: int,
    record_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await delete_growth_record(db, user.id, pet_id, record_id)
    return {"message": "Growth record deleted"}


@router.get("/{pet_id}/reminders", response_model=list[PetHealthReminderResponse])
async def list_my_pet_reminders(
    pet_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PetHealthReminder]:
    return await get_reminders(db, user.id, pet_id)


@router.post("/{pet_id}/reminders", response_model=PetHealthReminderResponse)
async def create_my_pet_reminder(
    pet_id: int,
    payload: PetHealthReminderCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PetHealthReminder:
    return await create_reminder(db, user.id, pet_id, payload)


@router.put("/{pet_id}/reminders/{reminder_id}", response_model=PetHealthReminderResponse)
async def update_my_pet_reminder(
    pet_id: int,
    reminder_id: int,
    payload: PetHealthReminderUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PetHealthReminder:
    return await update_reminder(db, user.id, pet_id, reminder_id, payload)


@router.delete("/{pet_id}/reminders/{reminder_id}")
async def delete_my_pet_reminder(
    pet_id: int,
    reminder_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await delete_reminder(db, user.id, pet_id, reminder_id)
    return {"message": "Reminder deleted"}


@router.get("/{pet_id}/detail-profile", response_model=PetDetailProfileResponse)
async def get_my_pet_detail_profile(
    pet_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PetDetailProfile:
    return await get_detail_profile(db, user.id, pet_id)


@router.put("/{pet_id}/detail-profile", response_model=PetDetailProfileResponse)
async def update_my_pet_detail_profile(
    pet_id: int,
    payload: PetDetailProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PetDetailProfile:
    return await update_detail_profile(db, user.id, pet_id, payload)


@router.get("/{pet_id}/profile-completeness", response_model=PetProfileCompletenessResponse)
async def get_my_pet_profile_completeness(
    pet_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await get_profile_completeness(db, user.id, pet_id)


@router.post("/{pet_id}/profile-document/preview", response_model=PetProfileDocumentPreviewResponse)
async def preview_my_pet_profile_document(
    pet_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await preview_profile_document(db, user.id, pet_id)
