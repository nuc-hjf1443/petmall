from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import bad_request, conflict, not_found
from models.adoption import AdoptionApplication, AdoptionPet
from models.user import User
from schemas.adoption_schema import AdoptionApplicationCreate, AdoptionPetCreate
from services.audit_service import write_audit_log


async def list_public_adoptions(db: AsyncSession) -> list[AdoptionPet]:
    result = await db.execute(
        select(AdoptionPet)
        .where(AdoptionPet.status == "published", AdoptionPet.is_deleted.is_(False))
        .order_by(AdoptionPet.created_at.desc(), AdoptionPet.id.desc())
    )
    return list(result.scalars().all())


async def get_public_adoption(db: AsyncSession, adoption_id: int) -> AdoptionPet:
    result = await db.execute(
        select(AdoptionPet).where(
            AdoptionPet.id == adoption_id,
            AdoptionPet.status == "published",
            AdoptionPet.is_deleted.is_(False),
        )
    )
    adoption = result.scalar_one_or_none()
    if adoption is None:
        raise not_found("Adoption pet not found")
    return adoption


async def create_adoption_pet(db: AsyncSession, user: User, payload: AdoptionPetCreate) -> AdoptionPet:
    adoption = AdoptionPet(publisher_id=user.id, **payload.model_dump())
    db.add(adoption)
    await db.commit()
    await db.refresh(adoption)
    return adoption


async def apply_adoption(
    db: AsyncSession,
    user: User,
    adoption_id: int,
    payload: AdoptionApplicationCreate,
) -> AdoptionApplication:
    adoption = await get_public_adoption(db, adoption_id)
    if adoption.publisher_id == user.id:
        raise bad_request("Publisher cannot apply for own adoption pet")
    existing = await db.execute(
        select(AdoptionApplication).where(
            AdoptionApplication.adoption_pet_id == adoption_id,
            AdoptionApplication.applicant_id == user.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise conflict("Adoption application already exists")

    application = AdoptionApplication(
        adoption_pet_id=adoption_id,
        applicant_id=user.id,
        **payload.model_dump(),
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application


async def list_my_applications(db: AsyncSession, user_id: int) -> list[AdoptionApplication]:
    result = await db.execute(
        select(AdoptionApplication)
        .where(AdoptionApplication.applicant_id == user_id)
        .order_by(AdoptionApplication.created_at.desc(), AdoptionApplication.id.desc())
    )
    return list(result.scalars().all())


async def list_admin_applications(db: AsyncSession, status: str | None = None) -> list[AdoptionApplication]:
    statement = select(AdoptionApplication).order_by(
        AdoptionApplication.created_at.desc(),
        AdoptionApplication.id.desc(),
    )
    if status:
        statement = statement.where(AdoptionApplication.status == status)
    result = await db.execute(statement)
    return list(result.scalars().all())


async def audit_adoption_application(
    db: AsyncSession,
    admin: User,
    application_id: int,
    approved: bool,
    reason: str | None,
) -> AdoptionApplication:
    application = await db.get(AdoptionApplication, application_id)
    if application is None:
        raise not_found("Adoption application not found")
    if application.status != "pending":
        raise conflict("Adoption application was already audited")

    application.status = "approved" if approved else "rejected"
    application.audit_reason = reason
    application.audited_by = admin.id
    application.audited_at = datetime.now(timezone.utc).isoformat()
    await write_audit_log(
        db,
        target_type="adoption_application",
        target_id=application.id,
        action="approve" if approved else "reject",
        result=application.status,
        operator_id=admin.id,
        reason=reason,
    )
    await db.commit()
    await db.refresh(application)
    return application
