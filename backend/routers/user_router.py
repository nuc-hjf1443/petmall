from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_db
from models.user import User, UserAddress
from schemas.auth_schema import ChangePasswordRequest
from schemas.user_schema import UserAddressCreate, UserAddressResponse, UserAddressUpdate, UserProfileUpdate, UserResponse
from services.auth_service import change_password
from services.user_service import (
    create_address,
    delete_address,
    get_addresses,
    set_default_address,
    update_address,
    update_user_profile,
)


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.put("/me/profile", response_model=UserResponse)
async def update_me_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await update_user_profile(db, current_user, payload)


@router.post("/me/change-password")
async def change_my_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await change_password(db, current_user, payload.old_password, payload.new_password)
    return {"message": "Password changed"}


@router.get("/me/addresses", response_model=list[UserAddressResponse])
async def list_addresses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserAddress]:
    return await get_addresses(db, current_user.id)


@router.post("/me/addresses", response_model=UserAddressResponse)
async def create_my_address(
    payload: UserAddressCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserAddress:
    return await create_address(db, current_user.id, payload)


@router.put("/me/addresses/{address_id}", response_model=UserAddressResponse)
async def update_my_address(
    address_id: int,
    payload: UserAddressUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserAddress:
    return await update_address(db, current_user.id, address_id, payload)


@router.delete("/me/addresses/{address_id}")
async def delete_my_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await delete_address(db, current_user.id, address_id)
    return {"message": "Address deleted"}


@router.post("/me/addresses/{address_id}/default", response_model=UserAddressResponse)
async def set_my_default_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserAddress:
    return await set_default_address(db, current_user.id, address_id)
