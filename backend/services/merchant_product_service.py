from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from models.merchant import Merchant
from schemas.merchant_schema import MerchantProductDiscountRequest, MerchantProductStatusRequest
from services.merchant_service import get_my_merchant


PRODUCT_MODULE_NOT_READY = "Product module not ready"


async def get_active_merchant_for_user(db: AsyncSession, user_id: int) -> Merchant:
    merchant = await get_my_merchant(db, user_id)
    if merchant.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Merchant is not approved"},
        )
    return merchant


def raise_product_module_not_ready() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={"code": "NOT_IMPLEMENTED", "message": PRODUCT_MODULE_NOT_READY},
    )


async def list_merchant_products(db: AsyncSession, user_id: int) -> list:
    await get_active_merchant_for_user(db, user_id)
    raise_product_module_not_ready()


async def submit_merchant_product(
    db: AsyncSession,
    user_id: int,
    product_id: int,
    payload: MerchantProductStatusRequest,
) -> dict:
    merchant = await get_active_merchant_for_user(db, user_id)
    raise_product_module_not_ready()
    return {"product_id": product_id, "merchant_id": merchant.id, "action": "submit", "status": "pending"}


async def set_merchant_product_on_sale(
    db: AsyncSession,
    user_id: int,
    product_id: int,
    payload: MerchantProductStatusRequest,
) -> dict:
    merchant = await get_active_merchant_for_user(db, user_id)
    raise_product_module_not_ready()
    return {"product_id": product_id, "merchant_id": merchant.id, "action": "on_sale", "status": "on_sale"}


async def set_merchant_product_off_sale(
    db: AsyncSession,
    user_id: int,
    product_id: int,
    payload: MerchantProductStatusRequest,
) -> dict:
    merchant = await get_active_merchant_for_user(db, user_id)
    raise_product_module_not_ready()
    return {"product_id": product_id, "merchant_id": merchant.id, "action": "off_sale", "status": "off_sale"}


async def set_merchant_product_discount(
    db: AsyncSession,
    user_id: int,
    product_id: int,
    payload: MerchantProductDiscountRequest,
) -> dict:
    merchant = await get_active_merchant_for_user(db, user_id)
    raise_product_module_not_ready()
    return {"product_id": product_id, "merchant_id": merchant.id, "action": "discount", "status": "discount_set"}
