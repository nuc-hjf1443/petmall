from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.order import Order, OrderItem, OrderRewardDelivery, PaymentTransaction
from models.product import CartItem, Product, ProductSku


async def get_cart_items_for_checkout(
    db: AsyncSession, user_id: int, item_ids: list[int]
) -> list[CartItem]:
    result = await db.execute(
        select(CartItem)
        .options(
            selectinload(CartItem.product).selectinload(Product.category),
            selectinload(CartItem.sku),
        )
        .where(CartItem.user_id == user_id, CartItem.id.in_(item_ids))
        .order_by(CartItem.id)
        .with_for_update()
    )
    return list(result.scalars().unique().all())


async def lock_skus(db: AsyncSession, sku_ids: list[int]) -> dict[int, ProductSku]:
    result = await db.execute(
        select(ProductSku)
        .options(selectinload(ProductSku.product).selectinload(Product.category))
        .where(ProductSku.id.in_(sorted(sku_ids)))
        .order_by(ProductSku.id)
        .with_for_update()
    )
    return {sku.id: sku for sku in result.scalars().unique().all()}


async def get_order(db: AsyncSession, order_id: int, user_id: int | None = None, lock: bool = False) -> Order | None:
    statement = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    if user_id is not None:
        statement = statement.where(Order.user_id == user_id)
    if lock:
        statement = statement.with_for_update()
    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def list_orders(db: AsyncSession, user_id: int) -> list[Order]:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc(), Order.id.desc())
    )
    return list(result.scalars().unique().all())


async def get_order_item(db: AsyncSession, item_id: int) -> OrderItem | None:
    result = await db.execute(
        select(OrderItem).options(selectinload(OrderItem.order)).where(OrderItem.id == item_id)
    )
    return result.scalar_one_or_none()


async def get_order_reward_delivery(
    db: AsyncSession, order_id: int, lock: bool = False
) -> OrderRewardDelivery | None:
    statement = select(OrderRewardDelivery).where(
        OrderRewardDelivery.order_id == order_id
    )
    if lock:
        statement = statement.with_for_update()
    return (await db.execute(statement)).scalar_one_or_none()


async def get_payment_by_business(
    db: AsyncSession,
    business_id: int,
    lock: bool = False,
    business_type: str = "order",
) -> PaymentTransaction | None:
    statement = select(PaymentTransaction).where(
        PaymentTransaction.business_type == business_type,
        PaymentTransaction.business_id == business_id,
    )
    if lock:
        statement = statement.with_for_update()
    return (await db.execute(statement)).scalar_one_or_none()


async def get_payment_by_trade_no(db: AsyncSession, out_trade_no: str, lock: bool = False) -> PaymentTransaction | None:
    statement = select(PaymentTransaction).where(PaymentTransaction.out_trade_no == out_trade_no)
    if lock:
        statement = statement.with_for_update()
    return (await db.execute(statement)).scalar_one_or_none()
