from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.errors import conflict, forbidden, not_found
from models.merchant import Merchant, MerchantQualification
from models.user import User
from schemas.merchant_schema import MerchantApplyRequest, MerchantUpdateRequest
from services.audit_service import write_audit_log


async def get_my_merchant(db: AsyncSession, user_id: int) -> Merchant:
    result = await db.execute(
        select(Merchant)
        .options(selectinload(Merchant.qualifications))
        .where(Merchant.owner_user_id == user_id)
    )
    merchant = result.scalar_one_or_none()
    if merchant is None:
        raise not_found("Merchant not found")
    return merchant


async def get_merchant_by_id(db: AsyncSession, merchant_id: int) -> Merchant:
    result = await db.execute(
        select(Merchant)
        .options(selectinload(Merchant.qualifications))
        .where(Merchant.id == merchant_id)
    )
    merchant = result.scalar_one_or_none()
    if merchant is None:
        raise not_found("Merchant not found")
    return merchant


async def apply_merchant(db: AsyncSession, user: User, payload: MerchantApplyRequest) -> Merchant:
    result = await db.execute(select(Merchant).where(Merchant.owner_user_id == user.id))
    existing = result.scalar_one_or_none()
    if existing is not None and existing.status in {"pending", "approved", "frozen"}:
        raise conflict("Merchant application already exists")

    merchant = Merchant(
        owner_user_id=user.id,
        shop_name=payload.shop_name,
        contact_name=payload.contact_name,
        contact_phone=payload.contact_phone,
        business_scope=payload.business_scope,
        city=payload.city,
        address=payload.address,
        description=payload.description,
        status="pending",
    )
    merchant.qualifications = [
        MerchantQualification(**qualification.model_dump())
        for qualification in payload.qualifications
    ]
    db.add(merchant)
    await db.commit()
    await db.refresh(merchant)
    return await get_my_merchant(db, user.id)


async def update_my_merchant(
    db: AsyncSession,
    user_id: int,
    payload: MerchantUpdateRequest,
) -> Merchant:
    merchant = await get_my_merchant(db, user_id)
    if merchant.status == "frozen":
        raise forbidden("Frozen merchant cannot be updated")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(merchant, field, value)
    await db.commit()
    return await get_my_merchant(db, user_id)


async def list_pending_merchants(db: AsyncSession) -> list[Merchant]:
    result = await db.execute(
        select(Merchant)
        .options(selectinload(Merchant.qualifications))
        .where(Merchant.status == "pending")
        .order_by(Merchant.created_at.asc(), Merchant.id.asc())
    )
    return list(result.scalars().all())


async def audit_merchant(
    db: AsyncSession,
    admin: User,
    merchant_id: int,
    approved: bool,
    reason: str | None,
) -> Merchant:
    merchant = await db.get(Merchant, merchant_id)
    if merchant is None:
        raise not_found("Merchant not found")
    if merchant.status != "pending":
        raise conflict("Merchant application was already audited")

    merchant.status = "approved" if approved else "rejected"
    merchant.audit_reason = reason
    owner = await db.get(User, merchant.owner_user_id)
    if owner is not None:
        owner.is_merchant = approved
    await write_audit_log(
        db,
        target_type="merchant",
        target_id=merchant.id,
        action="approve" if approved else "reject",
        result=merchant.status,
        operator_id=admin.id,
        reason=reason,
    )
    await db.commit()
    return await get_merchant_by_id(db, merchant.id)


async def get_merchant_for_product(db: AsyncSession, merchant_id: int) -> dict:
    merchant = await get_merchant_by_id(db, merchant_id)
    return {
        "id": merchant.id,
        "shop_name": merchant.shop_name,
        "status": merchant.status,
    }


async def ensure_merchant_active(db: AsyncSession, merchant_id: int) -> None:
    merchant = await get_merchant_by_id(db, merchant_id)
    if merchant.status != "approved":
        raise forbidden("Merchant is not active")
