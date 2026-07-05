from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db, require_admin
from models.user import User
from schemas.admin_schema import AdminLoginResponse, AdminReasonRequest, AdminUserResponse
from schemas.auth_schema import LoginRequest
from services.admin_service import admin_login, list_users, set_user_frozen


router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/login", response_model=AdminLoginResponse)
async def login_admin(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminLoginResponse:
    token = await admin_login(db, payload)
    return AdminLoginResponse(**token.model_dump())


@router.get("/users", response_model=list[AdminUserResponse])
async def admin_users(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[User]:
    return await list_users(db)


@router.post("/users/{user_id}/freeze", response_model=AdminUserResponse)
async def freeze_user(
    user_id: int,
    payload: AdminReasonRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await set_user_frozen(db, admin, user_id, True, payload.reason)


@router.post("/users/{user_id}/unfreeze", response_model=AdminUserResponse)
async def unfreeze_user(
    user_id: int,
    payload: AdminReasonRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await set_user_frozen(db, admin, user_id, False, payload.reason)


@router.get("/products/pending")
async def pending_products(_: User = Depends(require_admin)) -> list:
    return []


@router.get("/reports")
async def reports(_: User = Depends(require_admin)) -> list:
    return []
