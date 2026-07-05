from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import conflict, not_found
from models.user import User, UserAddress
from repository.user_repository import (
    get_latest_active_address,
    get_or_create_profile,
    get_user_address,
    get_user_by_email,
    list_user_addresses,
    unset_default_addresses,
)
from schemas.user_schema import UserAddressCreate, UserAddressUpdate, UserProfileUpdate


async def update_user_profile(db: AsyncSession, user: User, payload: UserProfileUpdate) -> User:
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"] and data["email"] != user.email:
        existing = await get_user_by_email(db, data["email"])
        if existing and existing.id != user.id:
            raise conflict("Email already registered")

    for field in ("email", "nickname", "avatar", "city"):
        if field in data:
            setattr(user, field, data[field])

    profile = await get_or_create_profile(db, user)
    for field in (
        "pet_experience",
        "living_city",
        "living_environment",
        "budget_preference",
        "preferred_categories",
        "feeding_philosophy",
        "allergy_notes",
    ):
        if field in data:
            setattr(profile, field, data[field])

    await db.commit()
    await db.refresh(user)
    return user


async def get_addresses(db: AsyncSession, user_id: int) -> list[UserAddress]:
    return await list_user_addresses(db, user_id)


async def create_address(db: AsyncSession, user_id: int, payload: UserAddressCreate) -> UserAddress:
    addresses = await list_user_addresses(db, user_id)
    should_default = payload.is_default or not addresses
    if should_default:
        await unset_default_addresses(db, user_id)
    address = UserAddress(user_id=user_id, **payload.model_dump())
    address.is_default = should_default
    db.add(address)
    await db.commit()
    await db.refresh(address)
    return address


async def update_address(
    db: AsyncSession,
    user_id: int,
    address_id: int,
    payload: UserAddressUpdate,
) -> UserAddress:
    address = await get_user_address(db, user_id, address_id)
    if address is None:
        raise not_found("Address not found")
    data = payload.model_dump(exclude_unset=True)
    is_default = data.pop("is_default", None)
    for field, value in data.items():
        setattr(address, field, value)
    if is_default is True:
        await unset_default_addresses(db, user_id)
        address.is_default = True
    elif is_default is False:
        address.is_default = False
    await db.commit()
    await db.refresh(address)
    return address


async def delete_address(db: AsyncSession, user_id: int, address_id: int) -> None:
    address = await get_user_address(db, user_id, address_id)
    if address is None:
        raise not_found("Address not found")
    was_default = address.is_default
    address.is_deleted = True
    address.is_default = False
    await db.flush()
    if was_default:
        next_default = await get_latest_active_address(db, user_id)
        if next_default is not None:
            next_default.is_default = True
    await db.commit()


async def set_default_address(db: AsyncSession, user_id: int, address_id: int) -> UserAddress:
    address = await get_user_address(db, user_id, address_id)
    if address is None:
        raise not_found("Address not found")
    await unset_default_addresses(db, user_id)
    address.is_default = True
    await db.commit()
    await db.refresh(address)
    return address


async def get_address_snapshot(db: AsyncSession, user_id: int, address_id: int) -> dict:
    address = await get_user_address(db, user_id, address_id)
    if address is None:
        raise not_found("Address not found")
    return {
        "receiver_name": address.receiver_name,
        "receiver_phone": address.receiver_phone,
        "province": address.province,
        "city": address.city,
        "district": address.district,
        "detail_address": address.detail_address,
        "postal_code": address.postal_code,
    }
