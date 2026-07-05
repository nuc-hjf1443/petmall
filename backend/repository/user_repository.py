from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.user import User, UserAddress, UserProfile


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(
        select(User)
        .options(selectinload(User.profile))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_phone(db: AsyncSession, phone: str) -> User | None:
    result = await db.execute(select(User).where(User.phone == phone))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_account(db: AsyncSession, account: str) -> User | None:
    result = await db.execute(
        select(User).where(or_(User.phone == account, User.email == account))
    )
    return result.scalar_one_or_none()


async def add_user(db: AsyncSession, user: User) -> User:
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def get_or_create_profile(db: AsyncSession, user: User) -> UserProfile:
    if user.profile is not None:
        return user.profile
    profile = UserProfile(user_id=user.id)
    db.add(profile)
    await db.flush()
    await db.refresh(profile)
    user.profile = profile
    return profile


async def list_user_addresses(db: AsyncSession, user_id: int) -> list[UserAddress]:
    result = await db.execute(
        select(UserAddress)
        .where(UserAddress.user_id == user_id, UserAddress.is_deleted.is_(False))
        .order_by(UserAddress.is_default.desc(), UserAddress.updated_at.desc(), UserAddress.id.desc())
    )
    return list(result.scalars().all())


async def get_user_address(db: AsyncSession, user_id: int, address_id: int) -> UserAddress | None:
    result = await db.execute(
        select(UserAddress).where(
            UserAddress.id == address_id,
            UserAddress.user_id == user_id,
            UserAddress.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()


async def get_latest_active_address(db: AsyncSession, user_id: int) -> UserAddress | None:
    result = await db.execute(
        select(UserAddress)
        .where(UserAddress.user_id == user_id, UserAddress.is_deleted.is_(False))
        .order_by(UserAddress.updated_at.desc(), UserAddress.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def unset_default_addresses(db: AsyncSession, user_id: int) -> None:
    addresses = await list_user_addresses(db, user_id)
    for address in addresses:
        address.is_default = False
