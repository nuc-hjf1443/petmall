from datetime import date, timedelta

from sqlalchemy import Select, func, or_, select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.errors import bad_request, forbidden, not_found
from models.base import utc_now
from models.merchant import Merchant
from models.order import Order, OrderStatus, PaymentStatus, PaymentTransaction
from models.pet import PetDetailProfile, PetProfile
from models.product import Product
from models.user import User
from schemas.admin_schema import (
    AdminOrderListResponse,
    AdminOrderResponse,
    AdminOrderTrendItem,
    AdminOrderTrendResponse,
    AdminOverviewResponse,
    AdminPetListResponse,
    AdminPetResponse,
)
from schemas.auth_schema import LoginRequest, TokenResponse
from schemas.order_schema import OrderItemResponse
from repository.order_repository import get_order, get_payment_by_business, lock_skus
from services.audit_service import write_admin_action_log
from services.auth_service import login_user


async def admin_login(db: AsyncSession, payload: LoginRequest) -> TokenResponse:
    token = await login_user(db, payload)
    result = await db.execute(
        select(User).where((User.phone == payload.account) | (User.email == payload.account))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_admin:
        raise forbidden("Admin permission required")
    return token


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at.desc(), User.id.desc()))
    return list(result.scalars().all())


async def set_user_frozen(
    db: AsyncSession,
    admin: User,
    user_id: int,
    frozen: bool,
    reason: str | None,
) -> User:
    user = await db.get(User, user_id)
    if user is None or user.is_deleted:
        raise not_found("User not found")
    user.is_frozen = frozen
    user.token_version += 1
    await write_admin_action_log(
        db,
        admin_id=admin.id,
        action="freeze" if frozen else "unfreeze",
        target_type="user",
        target_id=user.id,
        reason=reason,
    )
    await db.commit()
    await db.refresh(user)
    return user


def _page_bounds(page: int, page_size: int) -> tuple[int, int]:
    bounded_page = max(page, 1)
    bounded_size = min(max(page_size, 1), 100)
    return bounded_page, bounded_size


async def list_admin_pets(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    user_id: int | None,
    pet_type: str | None,
    keyword: str | None,
    is_deleted: bool | None,
) -> AdminPetListResponse:
    page, page_size = _page_bounds(page, page_size)
    filters = []
    if user_id is not None:
        filters.append(PetProfile.user_id == user_id)
    if pet_type:
        filters.append(PetProfile.pet_type == pet_type)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(PetProfile.name.ilike(pattern), PetProfile.breed.ilike(pattern)))
    if is_deleted is not None:
        filters.append(PetProfile.is_deleted.is_(is_deleted))

    total = int((await db.scalar(select(func.count(PetProfile.id)).where(*filters))) or 0)
    rows = await db.execute(
        select(PetProfile, User, PetDetailProfile.profile_completeness)
        .join(User, User.id == PetProfile.user_id)
        .outerjoin(PetDetailProfile, PetDetailProfile.pet_id == PetProfile.id)
        .where(*filters)
        .order_by(PetProfile.updated_at.desc(), PetProfile.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [
        AdminPetResponse(
            id=pet.id,
            user_id=pet.user_id,
            owner_phone=user.phone,
            owner_nickname=user.nickname,
            name=pet.name,
            pet_type=pet.pet_type,
            breed=pet.breed,
            gender=pet.gender,
            avatar=pet.avatar,
            profile_completeness=completeness,
            is_deleted=pet.is_deleted,
            created_at=pet.created_at,
            updated_at=pet.updated_at,
        )
        for pet, user, completeness in rows.all()
    ]
    return AdminPetListResponse(items=items, total=total, page=page, page_size=page_size)


def _admin_order_response(
    order: Order,
    user: User | None,
    merchant: Merchant | None,
    payment: PaymentTransaction | None,
) -> AdminOrderResponse:
    return AdminOrderResponse(
        id=order.id,
        order_no=order.order_no,
        user_id=order.user_id,
        user_phone=user.phone if user else None,
        merchant_id=order.merchant_id,
        merchant_name=merchant.shop_name if merchant else None,
        total_amount=order.total_amount,
        discount_amount=order.discount_amount,
        coin_deduct_amount=order.coin_deduct_amount,
        pay_amount=order.pay_amount,
        status=order.status,
        payment_status=payment.status if payment else None,
        payment_mode=payment.payment_mode if payment else None,
        out_trade_no=payment.out_trade_no if payment else None,
        address_snapshot=order.address_snapshot,
        paid_at=order.paid_at,
        completed_at=order.completed_at,
        cancelled_at=order.cancelled_at,
        created_at=order.created_at,
        items=[OrderItemResponse.model_validate(item, from_attributes=True) for item in order.items],
    )


def _order_filters(
    *,
    status: str | None,
    user_id: int | None,
    merchant_id: int | None,
    order_no: str | None,
    created_from: date | None,
    created_to: date | None,
) -> list:
    filters = []
    if status:
        filters.append(Order.status == status)
    if user_id is not None:
        filters.append(Order.user_id == user_id)
    if merchant_id is not None:
        filters.append(Order.merchant_id == merchant_id)
    if order_no:
        filters.append(Order.order_no.ilike(f"%{order_no.strip()}%"))
    if created_from is not None:
        filters.append(func.date(Order.created_at) >= created_from.isoformat())
    if created_to is not None:
        filters.append(func.date(Order.created_at) <= created_to.isoformat())
    return filters


def _admin_order_statement(filters: list) -> Select:
    return (
        select(Order, User, Merchant, PaymentTransaction)
        .join(User, User.id == Order.user_id, isouter=True)
        .join(Merchant, Merchant.id == Order.merchant_id, isouter=True)
        .join(
            PaymentTransaction,
            (PaymentTransaction.business_type == "order")
            & (PaymentTransaction.business_id == Order.id),
            isouter=True,
        )
        .options(selectinload(Order.items))
        .where(*filters)
    )


async def list_admin_orders(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    status: str | None,
    user_id: int | None,
    merchant_id: int | None,
    order_no: str | None,
    created_from: date | None,
    created_to: date | None,
) -> AdminOrderListResponse:
    page, page_size = _page_bounds(page, page_size)
    filters = _order_filters(
        status=status,
        user_id=user_id,
        merchant_id=merchant_id,
        order_no=order_no,
        created_from=created_from,
        created_to=created_to,
    )
    total = int((await db.scalar(select(func.count(Order.id)).where(*filters))) or 0)
    rows = await db.execute(
        _admin_order_statement(filters)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_admin_order_response(order, user, merchant, payment) for order, user, merchant, payment in rows.unique()]
    return AdminOrderListResponse(items=items, total=total, page=page, page_size=page_size)


async def get_admin_order(db: AsyncSession, order_id: int) -> AdminOrderResponse:
    row = (await db.execute(_admin_order_statement([Order.id == order_id]))).unique().first()
    if row is None:
        raise not_found("Order not found")
    order, user, merchant, payment = row
    return _admin_order_response(order, user, merchant, payment)


async def force_cancel_order(
    db: AsyncSession,
    admin: User,
    order_id: int,
    reason: str | None,
    *,
    commit: bool = True,
) -> AdminOrderResponse:
    order = await get_order(db, order_id, lock=True)
    if order is None:
        raise not_found("Order not found")
    if order.status == OrderStatus.CANCELLED.value:
        return await get_admin_order(db, order.id)
    if order.status in {
        OrderStatus.COMPLETED.value,
        OrderStatus.REFUNDED.value,
        OrderStatus.AFTER_SALE.value,
    }:
        raise bad_request("Order cannot be force cancelled in current status")

    skus = await lock_skus(db, [item.sku_id for item in order.items])
    for item in order.items:
        sku = skus.get(item.sku_id)
        if sku is not None:
            sku.stock += item.quantity
        await db.execute(
            update(Product)
            .where(Product.id == item.product_id)
            .values(stock=Product.stock + item.quantity)
            .execution_options(synchronize_session=False)
        )

    payment = await get_payment_by_business(db, order.id, lock=True)
    if payment is not None:
        if payment.status == PaymentStatus.PAID.value:
            payment.status = PaymentStatus.REFUNDED.value
        elif payment.status not in {PaymentStatus.REFUNDED.value, PaymentStatus.CLOSED.value}:
            payment.status = PaymentStatus.CLOSED.value

    order.status = OrderStatus.CANCELLED.value
    order.cancelled_at = utc_now()
    await write_admin_action_log(
        db,
        admin_id=admin.id,
        action="force_cancel",
        target_type="order",
        target_id=order.id,
        reason=reason,
    )
    if commit:
        await db.commit()
    else:
        await db.flush()
    return await get_admin_order(db, order.id)


async def get_admin_overview(db: AsyncSession) -> AdminOverviewResponse:
    paid_statuses = [PaymentStatus.PAID.value, PaymentStatus.REFUNDED.value]
    gmv = int(
        (
            await db.scalar(
                select(func.coalesce(func.sum(Order.pay_amount), 0))
                .join(
                    PaymentTransaction,
                    (PaymentTransaction.business_type == "order")
                    & (PaymentTransaction.business_id == Order.id),
                )
                .where(PaymentTransaction.status.in_(paid_statuses))
            )
        )
        or 0
    )
    order_count = int((await db.scalar(select(func.count(Order.id)))) or 0)
    paid_order_count = int(
        (
            await db.scalar(
                select(func.count(func.distinct(Order.id)))
                .join(
                    PaymentTransaction,
                    (PaymentTransaction.business_type == "order")
                    & (PaymentTransaction.business_id == Order.id),
                )
                .where(PaymentTransaction.status.in_(paid_statuses))
            )
        )
        or 0
    )
    pet_count = int(
        (await db.scalar(select(func.count(PetProfile.id)).where(PetProfile.is_deleted.is_(False)))) or 0
    )
    user_count = int(
        (await db.scalar(select(func.count(User.id)).where(User.is_deleted.is_(False)))) or 0
    )
    merchant_count = int((await db.scalar(select(func.count(Merchant.id)))) or 0)
    return AdminOverviewResponse(
        gmv=gmv,
        order_count=order_count,
        paid_order_count=paid_order_count,
        pet_count=pet_count,
        user_count=user_count,
        merchant_count=merchant_count,
    )


async def get_admin_order_trend(db: AsyncSession, *, days: int) -> AdminOrderTrendResponse:
    bounded_days = min(max(days, 1), 90)
    start_date = (utc_now() - timedelta(days=bounded_days - 1)).date()
    rows = await db.execute(
        select(
            func.date(Order.created_at).label("order_date"),
            func.count(func.distinct(Order.id)).label("order_count"),
            func.coalesce(func.sum(Order.pay_amount), 0).label("gmv"),
        )
        .join(
            PaymentTransaction,
            (PaymentTransaction.business_type == "order")
            & (PaymentTransaction.business_id == Order.id),
        )
        .where(
            PaymentTransaction.status.in_([PaymentStatus.PAID.value, PaymentStatus.REFUNDED.value]),
            func.date(Order.created_at) >= start_date.isoformat(),
        )
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
    )
    values = {str(row.order_date): (int(row.order_count), int(row.gmv or 0)) for row in rows}
    items = []
    for offset in range(bounded_days):
        current = start_date + timedelta(days=offset)
        count, gmv = values.get(current.isoformat(), (0, 0))
        items.append(AdminOrderTrendItem(date=current.isoformat(), order_count=count, gmv=gmv))
    return AdminOrderTrendResponse(items=items)
