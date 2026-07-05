from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_db
from models.user import User
from schemas.order_schema import OrderCreate, OrderResponse, PaymentResponse
from services.order_service import (
    CoinRewardAdapter,
    cancel_order,
    confirm_receipt,
    create_orders,
    get_coin_reward_adapter,
    get_user_order,
    get_user_orders,
)
from services.payment_service import create_order_payment


router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=list[OrderResponse])
async def create_my_orders(payload: OrderCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await create_orders(db, user.id, payload)


@router.get("", response_model=list[OrderResponse])
async def list_my_orders(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await get_user_orders(db, user.id)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_my_order(order_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await get_user_order(db, user.id, order_id)


@router.post("/{order_id}/pay", response_model=PaymentResponse)
async def pay_compat(order_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await create_order_payment(db, user.id, order_id)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_my_order(order_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await cancel_order(db, user.id, order_id)


@router.post("/{order_id}/confirm-receipt", response_model=OrderResponse)
async def confirm_my_receipt(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    adapter: CoinRewardAdapter = Depends(get_coin_reward_adapter),
):
    return await confirm_receipt(db, user.id, order_id, adapter)
