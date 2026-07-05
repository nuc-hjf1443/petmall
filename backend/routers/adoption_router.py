from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_db, require_admin
from models.adoption import AdoptionApplication, AdoptionPet
from models.user import User
from schemas.adoption_schema import (
    AdoptionApplicationCreate,
    AdoptionApplicationResponse,
    AdoptionPetCreate,
    AdoptionPetResponse,
    AuditDecision,
)
from services.adoption_service import (
    apply_adoption,
    audit_adoption_application,
    create_adoption_pet,
    get_public_adoption,
    list_admin_applications,
    list_my_applications,
    list_public_adoptions,
)


router = APIRouter(tags=["adoptions"])


@router.get("/adoptions", response_model=list[AdoptionPetResponse])
async def list_adoptions(db: AsyncSession = Depends(get_db)) -> list[AdoptionPet]:
    return await list_public_adoptions(db)


@router.get("/adoptions/applications/my", response_model=list[AdoptionApplicationResponse])
async def my_adoption_applications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AdoptionApplication]:
    return await list_my_applications(db, current_user.id)


@router.get("/adoptions/{adoption_id}", response_model=AdoptionPetResponse)
async def get_adoption(adoption_id: int, db: AsyncSession = Depends(get_db)) -> AdoptionPet:
    return await get_public_adoption(db, adoption_id)


@router.post("/adoptions", response_model=AdoptionPetResponse)
async def create_adoption(
    payload: AdoptionPetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AdoptionPet:
    return await create_adoption_pet(db, current_user, payload)


@router.post("/adoptions/{adoption_id}/applications", response_model=AdoptionApplicationResponse)
async def create_adoption_application(
    adoption_id: int,
    payload: AdoptionApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AdoptionApplication:
    return await apply_adoption(db, current_user, adoption_id, payload)


@router.get("/admin/adoptions/applications", response_model=list[AdoptionApplicationResponse])
async def admin_adoption_applications(
    status: str | None = None,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[AdoptionApplication]:
    return await list_admin_applications(db, status)


@router.post("/admin/adoptions/applications/{application_id}/approve", response_model=AdoptionApplicationResponse)
async def approve_adoption_application(
    application_id: int,
    payload: AuditDecision,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdoptionApplication:
    return await audit_adoption_application(db, admin, application_id, True, payload.reason)


@router.post("/admin/adoptions/applications/{application_id}/reject", response_model=AdoptionApplicationResponse)
async def reject_adoption_application(
    application_id: int,
    payload: AuditDecision,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdoptionApplication:
    return await audit_adoption_application(db, admin, application_id, False, payload.reason)
