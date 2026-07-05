from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_db
from models.user import User
from schemas.cart_schema import CartItemCreate, CartItemResponse, CartItemUpdate
from services.cart_service import (
    add_cart_item,
    delete_cart_item,
    get_user_cart,
    update_cart_item,
)


router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("/items", response_model=list[CartItemResponse])
async def list_my_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CartItemResponse]:
    return await get_user_cart(db, current_user.id)


@router.post("/items", response_model=CartItemResponse)
async def add_to_my_cart(
    payload: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartItemResponse:
    return await add_cart_item(db, current_user.id, payload)


@router.put("/items/{item_id}", response_model=CartItemResponse)
async def update_my_cart_item(
    item_id: int,
    payload: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartItemResponse:
    return await update_cart_item(db, current_user.id, item_id, payload)


@router.delete("/items/{item_id}")
async def delete_my_cart_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await delete_cart_item(db, current_user.id, item_id)
    return {"message": "Cart item deleted"}
