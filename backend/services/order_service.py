from collections import defaultdict
from typing import Protocol
from uuid import uuid4

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import bad_request, conflict, not_found
from models.base import utc_now
from models.order import Order, OrderItem, OrderRewardDelivery, OrderStatus, PaymentStatus
from models.product import Product, ProductStatus
from repository.order_repository import (
    get_cart_items_for_checkout,
    get_order,
    get_order_item,
    get_order_reward_delivery,
    list_orders,
    lock_skus,
)
from schemas.order_schema import OrderCreate, OrderItemResponse, OrderResponse
from services.user_service import get_address_snapshot


ORDER_REWARD_MAX_ATTEMPTS = 3


class CoinRewardAdapter(Protocol):
    async def grant_order_reward(
        self, *, user_id: int, order_id: int, pay_amount: int, idempotency_key: str
    ) -> None: ...


class DeferredCoinRewardAdapter:
    async def grant_order_reward(
        self, *, user_id: int, order_id: int, pay_amount: int, idempotency_key: str
    ) -> None:
        raise conflict("Coin reward integration is unavailable")


def get_coin_reward_adapter() -> CoinRewardAdapter:
    from services.coin_service import RealCoinRewardAdapter

    return RealCoinRewardAdapter()


def _response(order: Order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        order_no=order.order_no,
        merchant_id=order.merchant_id,
        total_amount=order.total_amount,
        discount_amount=order.discount_amount,
        coin_deduct_amount=order.coin_deduct_amount,
        pay_amount=order.pay_amount,
        status=order.status,
        address_snapshot=order.address_snapshot,
        paid_at=order.paid_at,
        completed_at=order.completed_at,
        created_at=order.created_at,
        items=[OrderItemResponse.model_validate(item, from_attributes=True) for item in order.items],
    )


async def create_orders(db: AsyncSession, user_id: int, payload: OrderCreate) -> list[OrderResponse]:
    if len(set(payload.cart_item_ids)) != len(payload.cart_item_ids):
        raise bad_request("Duplicate cart item id")
    address = await get_address_snapshot(db, user_id, payload.address_id)
    cart_items = await get_cart_items_for_checkout(db, user_id, payload.cart_item_ids)
    if len(cart_items) != len(payload.cart_item_ids):
        raise bad_request("Cart item not found or does not belong to current user")
    locked_skus = await lock_skus(db, [item.sku_id for item in cart_items])
    grouped: dict[int, list[tuple]] = defaultdict(list)
    try:
        for item in cart_items:
            sku = locked_skus.get(item.sku_id)
            if sku is None:
                raise bad_request("SKU not found")
            product = sku.product
            if (
                product.status != ProductStatus.ON_SALE.value
                or not product.category.is_enabled
                or not sku.is_enabled
            ):
                raise bad_request("Product is unavailable")
            if item.quantity > sku.stock or item.quantity > product.stock:
                raise bad_request("Insufficient stock")
            grouped[product.merchant_id].append((item, sku, product))

        orders: list[Order] = []
        for merchant_id, entries in grouped.items():
            order = Order(
                order_no=f"PM{utc_now():%Y%m%d%H%M%S}{uuid4().hex[:12].upper()}",
                user_id=user_id,
                merchant_id=merchant_id,
                total_amount=0,
                discount_amount=0,
                coin_deduct_amount=0,
                pay_amount=0,
                status=OrderStatus.PENDING_PAYMENT.value,
                address_snapshot=address,
            )
            for cart_item, sku, product in entries:
                subtotal = sku.price * cart_item.quantity
                order.items.append(
                    OrderItem(
                        product_id=product.id,
                        sku_id=sku.id,
                        product_title=product.title,
                        sku_name=sku.name,
                        sku_specs=dict(sku.specs),
                        product_image=product.cover_image,
                        unit_price=sku.price,
                        quantity=cart_item.quantity,
                        subtotal=subtotal,
                    )
                )
                order.total_amount += subtotal
                sku.stock -= cart_item.quantity
                stock_update = await db.execute(
                    update(Product)
                    .where(Product.id == product.id, Product.stock >= cart_item.quantity)
                    .values(stock=Product.stock - cart_item.quantity)
                    .execution_options(synchronize_session=False)
                )
                if stock_update.rowcount != 1:
                    raise bad_request("Insufficient stock")
                await db.delete(cart_item)
            order.pay_amount = order.total_amount
            db.add(order)
            orders.append(order)
        await db.commit()
        for order in orders:
            await db.refresh(order)
        return [_response(order) for order in orders]
    except Exception:
        await db.rollback()
        raise


async def get_user_orders(db: AsyncSession, user_id: int) -> list[OrderResponse]:
    return [_response(order) for order in await list_orders(db, user_id)]


async def get_user_order(db: AsyncSession, user_id: int, order_id: int) -> OrderResponse:
    order = await get_order(db, order_id, user_id)
    if order is None:
        raise not_found("Order not found")
    return _response(order)


async def cancel_order(db: AsyncSession, user_id: int, order_id: int) -> OrderResponse:
    order = await get_order(db, order_id, user_id, lock=True)
    if order is None:
        raise not_found("Order not found")
    if order.status == OrderStatus.CANCELLED.value:
        return _response(order)
    if order.status != OrderStatus.PENDING_PAYMENT.value:
        raise conflict("Order cannot be cancelled in current status")
    skus = await lock_skus(db, [item.sku_id for item in order.items])
    for item in order.items:
        sku = skus[item.sku_id]
        sku.stock += item.quantity
        await db.execute(
            update(Product)
            .where(Product.id == item.product_id)
            .values(stock=Product.stock + item.quantity)
            .execution_options(synchronize_session=False)
        )
    from repository.order_repository import get_payment_by_business

    payment = await get_payment_by_business(db, order.id, lock=True)
    if payment is not None and payment.status not in {
        PaymentStatus.PAID.value, PaymentStatus.REFUNDED.value
    }:
        payment.status = PaymentStatus.CLOSED.value
    order.status = OrderStatus.CANCELLED.value
    order.cancelled_at = utc_now()
    await db.commit()
    await db.refresh(order)
    return _response(order)


async def mark_order_paid(db: AsyncSession, order_id: int) -> None:
    order = await get_order(db, order_id, lock=True)
    if order is None:
        raise not_found("Order not found")
    if order.status == OrderStatus.PAID.value:
        return
    if order.status != OrderStatus.PENDING_PAYMENT.value:
        raise conflict("Order cannot be paid in current status")
    order.status = OrderStatus.PAID.value
    order.paid_at = utc_now()


async def transition_fulfillment(db: AsyncSession, order_id: int, target_status: str) -> None:
    order = await get_order(db, order_id, lock=True)
    if order is None:
        raise not_found("Order not found")
    allowed = {
        OrderStatus.PAID.value: OrderStatus.PENDING_SHIPMENT.value,
        OrderStatus.PENDING_SHIPMENT.value: OrderStatus.SHIPPED.value,
        OrderStatus.SHIPPED.value: OrderStatus.PENDING_RECEIPT.value,
    }
    if allowed.get(order.status) != target_status:
        raise bad_request("Invalid order status transition")
    order.status = target_status
    await db.commit()


async def _deliver_order_reward(
    db: AsyncSession,
    order: Order,
    delivery: OrderRewardDelivery,
    reward_adapter: CoinRewardAdapter,
) -> None:
    delivery.status = "pending"
    delivery.error_message = None
    for attempt in range(1, ORDER_REWARD_MAX_ATTEMPTS + 1):
        try:
            await reward_adapter.grant_order_reward(
                user_id=order.user_id,
                order_id=order.id,
                pay_amount=order.pay_amount,
                idempotency_key=delivery.idempotency_key,
            )
        except Exception as exc:
            if attempt == ORDER_REWARD_MAX_ATTEMPTS:
                delivery.status = "failed"
                delivery.error_message = str(exc)[:1000]
        else:
            delivery.status = "delivered"
            break
    await db.commit()


async def confirm_receipt(
    db: AsyncSession,
    user_id: int,
    order_id: int,
    reward_adapter: CoinRewardAdapter,
) -> OrderResponse:
    order = await get_order(db, order_id, user_id, lock=True)
    if order is None:
        raise not_found("Order not found")
    if order.status == OrderStatus.COMPLETED.value:
        delivery = await get_order_reward_delivery(db, order.id, lock=True)
        if delivery is None or delivery.status == "delivered":
            raise conflict("Order receipt already confirmed")
        await _deliver_order_reward(db, order, delivery, reward_adapter)
        await db.refresh(order)
        return _response(order)
    if order.status != OrderStatus.PENDING_RECEIPT.value:
        raise conflict("Order cannot be confirmed in current status")
    key = f"order:{order.id}:receipt_reward"
    delivery = OrderRewardDelivery(
        order_id=order.id, user_id=user_id, idempotency_key=key, status="pending"
    )
    order.status = OrderStatus.COMPLETED.value
    order.completed_at = utc_now()
    db.add(delivery)
    await db.commit()
    await _deliver_order_reward(db, order, delivery, reward_adapter)
    await db.refresh(order)
    return _response(order)


async def verify_completed_purchase(
    db: AsyncSession, *, user_id: int, order_item_id: int
):
    from services.review_service import ReviewPurchase

    item = await get_order_item(db, order_item_id)
    if item is None or item.order.user_id != user_id or item.order.status != OrderStatus.COMPLETED.value:
        raise conflict("A completed purchase is required")
    return ReviewPurchase(order_item_id=item.id, product_id=item.product_id, sku_id=item.sku_id)
