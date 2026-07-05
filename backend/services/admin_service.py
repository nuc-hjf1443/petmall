from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import forbidden, not_found
from models.user import User
from schemas.auth_schema import LoginRequest, TokenResponse
from services.audit_service import write_admin_action_log
from services.auth_service import login_user


async def admin_login(db: AsyncSession, payload: LoginRequest) -> TokenResponse:
    token = await login_user(db, payload)
    result = await db.execute(
        select(User).where((User.phone == payload.account) | (User.email == payload.account))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_admin:
        raise forbidden("Admin permission required")
    return token


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at.desc(), User.id.desc()))
    return list(result.scalars().all())


async def set_user_frozen(
    db: AsyncSession,
    admin: User,
    user_id: int,
    frozen: bool,
    reason: str | None,
) -> User:
    user = await db.get(User, user_id)
    if user is None or user.is_deleted:
        raise not_found("User not found")
    user.is_frozen = frozen
    user.token_version += 1
    await write_admin_action_log(
        db,
        admin_id=admin.id,
        action="freeze" if frozen else "unfreeze",
        target_type="user",
        target_id=user.id,
        reason=reason,
    )
    await db.commit()
    await db.refresh(user)
    return user
