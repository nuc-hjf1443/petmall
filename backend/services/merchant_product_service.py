from sqlalchemy.ext.asyncio import AsyncSession

from models.merchant import Merchant
from schemas.merchant_schema import MerchantProductDiscountRequest, MerchantProductStatusRequest
from schemas.product_schema import ProductCreate, ProductUpdate
from services.merchant_service import get_my_merchant
from services.product_service import (
    create_merchant_product,
    get_products_for_merchant,
    set_merchant_product_sale_status,
    submit_product_for_audit,
    update_merchant_product,
    update_merchant_product_discount,
)
from core.errors import bad_request, forbidden


async def get_active_merchant_for_user(db: AsyncSession, user_id: int) -> Merchant:
    merchant = await get_my_merchant(db, user_id)
    if merchant.status != "approved":
        raise forbidden("Merchant is not approved")
    return merchant


async def list_merchant_products(db: AsyncSession, user_id: int) -> list:
    merchant = await get_active_merchant_for_user(db, user_id)
    products = await get_products_for_merchant(db, merchant.id)
    return [
        {
            "id": product.id,
            "merchant_id": product.merchant_id,
            "category_id": product.category_id,
            "title": product.title,
            "cover_image": product.cover_image,
            "price": product.price,
            "original_price": product.original_price,
            "stock": product.stock,
            "status": product.status,
            "audit_reason": product.audit_reason,
            "submitted_at": product.submitted_at,
            "audited_at": product.audited_at,
            "created_at": product.created_at,
            "updated_at": product.updated_at,
        }
        for product in products
    ]


async def create_product_for_merchant(
    db: AsyncSession,
    user_id: int,
    payload: ProductCreate,
) -> dict:
    merchant = await get_active_merchant_for_user(db, user_id)
    product = await create_merchant_product(db, merchant.id, payload)
    return product.model_dump()


async def update_product_for_merchant(
    db: AsyncSession,
    user_id: int,
    product_id: int,
    payload: ProductUpdate,
) -> dict:
    merchant = await get_active_merchant_for_user(db, user_id)
    product = await update_merchant_product(db, merchant.id, product_id, payload)
    return product.model_dump()


async def submit_merchant_product(
    db: AsyncSession,
    user_id: int,
    product_id: int,
    payload: MerchantProductStatusRequest,
) -> dict:
    merchant = await get_active_merchant_for_user(db, user_id)
    product = await submit_product_for_audit(db, merchant.id, product_id)
    return {"product_id": product.id, "merchant_id": merchant.id, "action": "submit", "status": product.status}


async def set_merchant_product_on_sale(
    db: AsyncSession,
    user_id: int,
    product_id: int,
    payload: MerchantProductStatusRequest,
) -> dict:
    merchant = await get_active_merchant_for_user(db, user_id)
    product = await set_merchant_product_sale_status(db, merchant.id, product_id, on_sale=True)
    return {"product_id": product.id, "merchant_id": merchant.id, "action": "on_sale", "status": product.status}


async def set_merchant_product_off_sale(
    db: AsyncSession,
    user_id: int,
    product_id: int,
    payload: MerchantProductStatusRequest,
) -> dict:
    merchant = await get_active_merchant_for_user(db, user_id)
    product = await set_merchant_product_sale_status(db, merchant.id, product_id, on_sale=False)
    return {"product_id": product.id, "merchant_id": merchant.id, "action": "off_sale", "status": product.status}


async def set_merchant_product_discount(
    db: AsyncSession,
    user_id: int,
    product_id: int,
    payload: MerchantProductDiscountRequest,
) -> dict:
    merchant = await get_active_merchant_for_user(db, user_id)
    sku_prices = dict(payload.sku_prices)
    if not sku_prices:
        raise bad_request("sku_prices is required")
    product = await update_merchant_product_discount(db, merchant.id, product_id, sku_prices)
    return {"product_id": product.id, "merchant_id": merchant.id, "action": "discount", "status": product.status}
