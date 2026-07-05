from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.product import CartItem, Product


def _cart_options():
    return (
        selectinload(CartItem.product).selectinload(Product.category),
        selectinload(CartItem.sku),
    )


async def list_cart_items(db: AsyncSession, user_id: int) -> list[CartItem]:
    result = await db.execute(
        select(CartItem)
        .options(*_cart_options())
        .where(CartItem.user_id == user_id)
        .order_by(CartItem.updated_at.desc(), CartItem.id.desc())
    )
    return list(result.scalars().all())


async def get_cart_item(db: AsyncSession, user_id: int, item_id: int) -> CartItem | None:
    result = await db.execute(
        select(CartItem)
        .options(*_cart_options())
        .where(CartItem.id == item_id, CartItem.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_cart_item_by_sku(db: AsyncSession, user_id: int, sku_id: int) -> CartItem | None:
    result = await db.execute(
        select(CartItem)
        .options(*_cart_options())
        .where(CartItem.user_id == user_id, CartItem.sku_id == sku_id)
    )
    return result.scalar_one_or_none()
