from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db, require_admin
from models.user import User
from schemas.admin_schema import AdminLoginResponse, AdminReasonRequest, AdminReportResolveRequest, AdminUserResponse
from schemas.auth_schema import LoginRequest
from services.admin_service import admin_login, list_users, set_user_frozen
from services.audit_service import write_audit_log
from services.community_service import list_reports, resolve_report
from services.product_service import get_pending_products_for_audit, update_product_audit_status
from models.product import ProductStatus


router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/login", response_model=AdminLoginResponse)
async def login_admin(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminLoginResponse:
    token = await admin_login(db, payload)
    return AdminLoginResponse(**token.model_dump())


@router.get("/users", response_model=list[AdminUserResponse])
async def admin_users(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[User]:
    return await list_users(db)


@router.post("/users/{user_id}/freeze", response_model=AdminUserResponse)
async def freeze_user(
    user_id: int,
    payload: AdminReasonRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await set_user_frozen(db, admin, user_id, True, payload.reason)


@router.post("/users/{user_id}/unfreeze", response_model=AdminUserResponse)
async def unfreeze_user(
    user_id: int,
    payload: AdminReasonRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await set_user_frozen(db, admin, user_id, False, payload.reason)


@router.get("/products/pending")
async def pending_products(
    page: int = 1,
    page_size: int = 20,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await get_pending_products_for_audit(db, page=page, page_size=page_size)


@router.post("/products/{product_id}/approve")
async def approve_product(
    product_id: int,
    payload: AdminReasonRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await update_product_audit_status(
        db,
        product_id,
        ProductStatus.ON_SALE.value,
        payload.reason,
        commit=False,
    )
    await write_audit_log(
        db,
        target_type="product",
        target_id=product_id,
        action="approve",
        result=ProductStatus.ON_SALE.value,
        operator_id=admin.id,
        reason=payload.reason,
    )
    await db.commit()
    return {"message": "Product approved"}


@router.post("/products/{product_id}/reject")
async def reject_product(
    product_id: int,
    payload: AdminReasonRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await update_product_audit_status(
        db,
        product_id,
        ProductStatus.REJECTED.value,
        payload.reason,
        commit=False,
    )
    await write_audit_log(
        db,
        target_type="product",
        target_id=product_id,
        action="reject",
        result=ProductStatus.REJECTED.value,
        operator_id=admin.id,
        reason=payload.reason,
    )
    await db.commit()
    return {"message": "Product rejected"}


@router.get("/reports")
async def reports(
    page: int = 1,
    page_size: int = 20,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await list_reports(db, max(page, 1), min(max(page_size, 1), 100))


@router.post("/reports/{report_id}/resolve")
async def resolve_report_api(
    report_id: int,
    payload: AdminReportResolveRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await resolve_report(
        db,
        report_id,
        payload.action,
        payload.reason,
        admin.id,
        commit=False,
    )
    await write_audit_log(
        db,
        target_type="report",
        target_id=report_id,
        action=payload.action,
        result="resolved",
        operator_id=admin.id,
        reason=payload.reason,
    )
    await db.commit()
    return {"message": "Report resolved"}
