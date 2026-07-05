from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import create_access_token, hash_password, verify_password
from core.cache import CacheBackend
from core.errors import bad_request, conflict, rate_limited, unauthorized
from models.user import User, UserProfile
from repository.user_repository import add_user, get_user_by_account, get_user_by_email, get_user_by_phone
from schemas.auth_schema import LoginRequest, RegisterRequest, TokenResponse
from services.sms_service import SmsService
from settings.config import get_settings


def _sms_code_key(phone: str) -> str:
    return f"sms:code:{phone}"


def _sms_cooldown_key(phone: str) -> str:
    return f"sms:cooldown:{phone}"


async def send_sms_code(cache: CacheBackend, sms_service: SmsService, phone: str) -> dict[str, str | None]:
    settings = get_settings()
    if await cache.get(_sms_cooldown_key(phone)):
        raise rate_limited("SMS code was sent recently")
    result = sms_service.send_verify_code(phone)
    if not result.success or result.code is None:
        raise bad_request(result.message)
    await cache.set(_sms_code_key(phone), result.code, ex=settings.sms_code_expire_seconds)
    await cache.set(_sms_cooldown_key(phone), "1", ex=settings.sms_send_cooldown_seconds)
    return {
        "message": "SMS code sent",
        "debug_code": result.code if settings.sms_debug_code_enabled else None,
    }


async def register_user(db: AsyncSession, cache: CacheBackend, payload: RegisterRequest) -> User:
    cached_code = await cache.get(_sms_code_key(payload.phone))
    if cached_code is None or cached_code != payload.sms_code:
        raise bad_request("SMS code invalid or expired")
    if await get_user_by_phone(db, payload.phone):
        raise conflict("Phone already registered")
    if payload.email and await get_user_by_email(db, payload.email):
        raise conflict("Email already registered")

    user = User(
        phone=payload.phone,
        email=payload.email,
        nickname=payload.nickname,
        password_hash=hash_password(payload.password),
    )
    user.profile = UserProfile()
    await add_user(db, user)
    await db.commit()
    await db.refresh(user)
    await cache.delete(_sms_code_key(payload.phone))
    return user


async def login_user(db: AsyncSession, payload: LoginRequest) -> TokenResponse:
    user = await get_user_by_account(db, payload.account)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise unauthorized("Account or password is incorrect")
    if user.is_frozen or user.is_deleted:
        raise unauthorized("User disabled or deleted")
    settings = get_settings()
    token = create_access_token(user.id, user.token_version)
    return TokenResponse(access_token=token, expires_in=settings.access_token_expire_minutes * 60)


async def refresh_token(user: User) -> TokenResponse:
    settings = get_settings()
    token = create_access_token(user.id, user.token_version)
    return TokenResponse(access_token=token, expires_in=settings.access_token_expire_minutes * 60)


async def change_password(db: AsyncSession, user: User, old_password: str, new_password: str) -> None:
    if not verify_password(old_password, user.password_hash):
        raise unauthorized("Old password is incorrect")
    user.password_hash = hash_password(new_password)
    user.token_version += 1
    await db.commit()
