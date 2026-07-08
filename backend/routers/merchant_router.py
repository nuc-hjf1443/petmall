from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_db, require_admin
from models.merchant import Merchant
from models.user import User
from schemas.merchant_schema import (
    MerchantApplyRequest,
    MerchantAuditDecision,
    MerchantDashboardResponse,
    MerchantProductActionResponse,
    MerchantProductDiscountRequest,
    MerchantProductResponse,
    MerchantProductStatusRequest,
    MerchantResponse,
    MerchantUpdateRequest,
)
from schemas.product_schema import ProductCreate, ProductUpdate
from services.merchant_service import (
    apply_merchant,
    audit_merchant,
    get_my_merchant,
    list_pending_merchants,
    update_my_merchant,
)
from services.merchant_product_service import (
    create_product_for_merchant,
    list_merchant_products,
    set_merchant_product_discount,
    set_merchant_product_off_sale,
    set_merchant_product_on_sale,
    submit_merchant_product,
    update_product_for_merchant,
)
from services.product_service import set_merchant_follow


router = APIRouter(tags=["merchants"])


@router.post("/merchants/apply", response_model=MerchantResponse)
async def apply_for_merchant(
    payload: MerchantApplyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Merchant:
    return await apply_merchant(db, current_user, payload)


@router.get("/merchants/me", response_model=MerchantResponse)
async def get_merchant_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Merchant:
    return await get_my_merchant(db, current_user.id)


@router.put("/merchants/me", response_model=MerchantResponse)
async def update_merchant_me(
    payload: MerchantUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Merchant:
    return await update_my_merchant(db, current_user.id, payload)


@router.post("/merchants/{merchant_id}/follow")
async def follow_merchant(
    merchant_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await set_merchant_follow(db, current_user.id, merchant_id, True)
    return {"message": "Merchant followed"}


@router.delete("/merchants/{merchant_id}/follow")
async def unfollow_merchant(
    merchant_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await set_merchant_follow(db, current_user.id, merchant_id, False)
    return {"message": "Merchant unfollowed"}


@router.get("/merchants/me/dashboard", response_model=MerchantDashboardResponse)
async def merchant_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MerchantDashboardResponse:
    merchant = await get_my_merchant(db, current_user.id)
    return MerchantDashboardResponse(merchant_id=merchant.id, status=merchant.status)


@router.get("/merchants/me/products")
async def merchant_products(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    return await list_merchant_products(db, current_user.id)


@router.post("/merchants/me/products", response_model=MerchantProductResponse)
async def create_merchant_product_api(
    payload: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return {"product": await create_product_for_merchant(db, current_user.id, payload)}


@router.put("/merchants/me/products/{product_id}", response_model=MerchantProductResponse)
async def update_merchant_product_api(
    product_id: int,
    payload: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return {"product": await update_product_for_merchant(db, current_user.id, product_id, payload)}


@router.post("/merchants/me/products/{product_id}/submit", response_model=MerchantProductActionResponse)
async def submit_product_for_audit(
    product_id: int,
    payload: MerchantProductStatusRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await submit_merchant_product(db, current_user.id, product_id, payload)


@router.post("/merchants/me/products/{product_id}/on-sale", response_model=MerchantProductActionResponse)
async def product_on_sale(
    product_id: int,
    payload: MerchantProductStatusRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await set_merchant_product_on_sale(db, current_user.id, product_id, payload)


@router.post("/merchants/me/products/{product_id}/off-sale", response_model=MerchantProductActionResponse)
async def product_off_sale(
    product_id: int,
    payload: MerchantProductStatusRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await set_merchant_product_off_sale(db, current_user.id, product_id, payload)


@router.post("/merchants/me/products/{product_id}/discount", response_model=MerchantProductActionResponse)
async def product_discount(
    product_id: int,
    payload: MerchantProductDiscountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await set_merchant_product_discount(db, current_user.id, product_id, payload)


@router.get("/admin/merchants/pending", response_model=list[MerchantResponse])
async def admin_pending_merchants(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[Merchant]:
    return await list_pending_merchants(db)


@router.post("/admin/merchants/{merchant_id}/approve", response_model=MerchantResponse)
async def approve_merchant(
    merchant_id: int,
    payload: MerchantAuditDecision,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Merchant:
    return await audit_merchant(db, admin, merchant_id, True, payload.reason)


@router.post("/admin/merchants/{merchant_id}/reject", response_model=MerchantResponse)
async def reject_merchant(
    merchant_id: int,
    payload: MerchantAuditDecision,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Merchant:
    return await audit_merchant(db, admin, merchant_id, False, payload.reason)
