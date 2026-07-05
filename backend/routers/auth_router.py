from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.cache import CacheBackend, get_cache
from core.dependencies import get_current_user, get_db
from models.user import User
from schemas.auth_schema import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    SmsCodeRequest,
    SmsCodeResponse,
    TokenResponse,
)
from schemas.user_schema import UserResponse
from services.auth_service import change_password, login_user, refresh_token, register_user, send_sms_code
from services.sms_service import SmsService, get_sms_service


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/code", response_model=SmsCodeResponse)
async def send_code(
    payload: SmsCodeRequest,
    cache: CacheBackend = Depends(get_cache),
    sms_service: SmsService = Depends(get_sms_service),
) -> dict[str, str | None]:
    return await send_sms_code(cache, sms_service, payload.phone)


@router.post("/register", response_model=UserResponse)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    cache: CacheBackend = Depends(get_cache),
) -> User:
    return await register_user(db, cache, payload)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    return await login_user(db, payload)


@router.post("/logout")
async def logout() -> dict[str, str]:
    return {"message": "Logged out"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(current_user: User = Depends(get_current_user)) -> TokenResponse:
    return await refresh_token(current_user)


@router.post("/change-password")
async def change_current_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await change_password(db, current_user, payload.old_password, payload.new_password)
    return {"message": "Password changed"}
