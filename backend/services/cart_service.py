from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import bad_request, not_found
from models.product import CartItem, ProductSku, ProductStatus
from repository.cart_repository import get_cart_item, get_cart_item_by_sku, list_cart_items
from repository.product_repository import get_sku_with_product
from schemas.cart_schema import CartItemCreate, CartItemResponse, CartItemUpdate


def _is_available(item: CartItem) -> bool:
    return (
        item.product.status == ProductStatus.ON_SALE.value
        and item.product.category.is_enabled
        and item.sku.is_enabled
        and item.quantity <= min(item.product.stock, item.sku.stock)
    )


def _serialize_cart_item(item: CartItem) -> CartItemResponse:
    return CartItemResponse(
        id=item.id,
        quantity=item.quantity,
        selected=item.selected,
        available=_is_available(item),
        subtotal=item.sku.price * item.quantity,
        product={
            "id": item.product.id,
            "merchant_id": item.product.merchant_id,
            "title": item.product.title,
            "cover_image": item.product.cover_image,
            "status": item.product.status,
        },
        sku={
            "id": item.sku.id,
            "sku_code": item.sku.sku_code,
            "name": item.sku.name,
            "specs": item.sku.specs,
            "price": item.sku.price,
            "stock": item.sku.stock,
            "is_enabled": item.sku.is_enabled,
        },
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _validate_purchase(sku: ProductSku, quantity: int) -> None:
    product = sku.product
    if product.status != ProductStatus.ON_SALE.value:
        raise bad_request("Product is not on sale")
    if not product.category.is_enabled:
        raise bad_request("Product category is disabled")
    if not sku.is_enabled:
        raise bad_request("SKU is disabled")
    available_stock = min(product.stock, sku.stock)
    if quantity > available_stock:
        raise bad_request("Insufficient stock")


async def get_user_cart(db: AsyncSession, user_id: int) -> list[CartItemResponse]:
    items = await list_cart_items(db, user_id)
    return [_serialize_cart_item(item) for item in items]


async def add_cart_item(
    db: AsyncSession,
    user_id: int,
    payload: CartItemCreate,
) -> CartItemResponse:
    sku = await get_sku_with_product(db, payload.sku_id)
    if sku is None:
        raise not_found("SKU not found")
    existing = await get_cart_item_by_sku(db, user_id, payload.sku_id)
    quantity = payload.quantity + (existing.quantity if existing else 0)
    if quantity > 99:
        raise bad_request("Cart item quantity cannot exceed 99")
    _validate_purchase(sku, quantity)

    if existing is None:
        item = CartItem(
            user_id=user_id,
            product_id=sku.product_id,
            sku_id=sku.id,
            quantity=quantity,
            selected=True,
        )
        item.product = sku.product
        item.sku = sku
        db.add(item)
    else:
        item = existing
        item.quantity = quantity

    await db.commit()
    await db.refresh(item)
    return _serialize_cart_item(item)


async def update_cart_item(
    db: AsyncSession,
    user_id: int,
    item_id: int,
    payload: CartItemUpdate,
) -> CartItemResponse:
    item = await get_cart_item(db, user_id, item_id)
    if item is None:
        raise not_found("Cart item not found")
    data = payload.model_dump(exclude_unset=True)
    if "quantity" in data:
        _validate_purchase(item.sku, data["quantity"])
        item.quantity = data["quantity"]
    if "selected" in data:
        item.selected = data["selected"]
    await db.commit()
    await db.refresh(item)
    return _serialize_cart_item(item)


async def delete_cart_item(db: AsyncSession, user_id: int, item_id: int) -> None:
    item = await get_cart_item(db, user_id, item_id)
    if item is None:
        raise not_found("Cart item not found")
    await db.delete(item)
    await db.commit()
