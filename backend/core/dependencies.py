from collections.abc import AsyncIterator

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import decode_access_token
from core.errors import forbidden, unauthorized
from models.database import AsyncSessionLocal
from models.user import User
from repository.user_repository import get_user_by_id


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    token_version = payload.get("token_version")
    if user_id is None or token_version is None:
        raise unauthorized("Token payload invalid")
    user = await get_user_by_id(db, int(user_id))
    if user is None or user.is_deleted or user.is_frozen:
        raise unauthorized("User disabled or not found")
    if user.token_version != int(token_version):
        raise unauthorized("Token version expired")
    return user


async def get_optional_current_user(
    token: str | None = Depends(optional_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if token is None:
        return None
    return await get_current_user(token, db)


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise forbidden("Admin permission required")
    return current_user


async def require_merchant(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_merchant:
        raise forbidden("Merchant permission required")
    return current_user
