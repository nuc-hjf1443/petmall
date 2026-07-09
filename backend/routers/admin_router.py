from datetime import date

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db, require_admin
from core.knowledge_queue import KnowledgeTaskPublisher, get_knowledge_task_publisher
from models.user import User
from schemas.admin_schema import (
    AdminLoginResponse,
    AdminOrderListResponse,
    AdminOrderResponse,
    AdminOrderTrendResponse,
    AdminOverviewResponse,
    AdminPetListResponse,
    AdminReasonRequest,
    AdminReportResolveRequest,
    AdminUserListResponse,
    AdminUserResponse,
)
from schemas.knowledge_schema import KnowledgeBaseResponse, KnowledgeDocumentResponse
from schemas.auth_schema import LoginRequest
from services.admin_service import (
    admin_login,
    force_cancel_order,
    get_admin_order,
    get_admin_order_trend,
    get_admin_overview,
    list_admin_orders,
    list_admin_pets,
    list_users,
    set_user_frozen,
)
from services.audit_service import write_audit_log
from services.community_service import list_reports, resolve_report
from services.knowledge_service import (
    delete_platform_document,
    get_platform_documents,
    get_platform_knowledge_base,
    reindex_platform_document,
    replace_platform_document,
    upload_platform_document,
)
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


@router.get("/users", response_model=AdminUserListResponse)
async def admin_users(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    role: str | None = None,
    is_frozen: bool | None = None,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUserListResponse:
    return await list_users(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        role=role,
        is_frozen=is_frozen,
    )


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


@router.get("/pets", response_model=AdminPetListResponse)
async def admin_pets(
    page: int = 1,
    page_size: int = 20,
    user_id: int | None = None,
    pet_type: str | None = None,
    keyword: str | None = None,
    is_deleted: bool | None = None,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminPetListResponse:
    return await list_admin_pets(
        db,
        page=page,
        page_size=page_size,
        user_id=user_id,
        pet_type=pet_type,
        keyword=keyword,
        is_deleted=is_deleted,
    )


@router.get("/orders", response_model=AdminOrderListResponse)
async def admin_orders(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    user_id: int | None = None,
    merchant_id: int | None = None,
    order_no: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminOrderListResponse:
    return await list_admin_orders(
        db,
        page=page,
        page_size=page_size,
        status=status,
        user_id=user_id,
        merchant_id=merchant_id,
        order_no=order_no,
        created_from=created_from,
        created_to=created_to,
    )


@router.get("/orders/{order_id}", response_model=AdminOrderResponse)
async def admin_order_detail(
    order_id: int,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminOrderResponse:
    return await get_admin_order(db, order_id)


@router.post("/orders/{order_id}/force-cancel", response_model=AdminOrderResponse)
async def admin_force_cancel_order(
    order_id: int,
    payload: AdminReasonRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminOrderResponse:
    return await force_cancel_order(db, admin, order_id, payload.reason)


@router.get("/statistics/overview", response_model=AdminOverviewResponse)
async def admin_statistics_overview(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminOverviewResponse:
    return await get_admin_overview(db)


@router.get("/statistics/orders-trend", response_model=AdminOrderTrendResponse)
async def admin_orders_trend(
    days: int = 30,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminOrderTrendResponse:
    return await get_admin_order_trend(db, days=days)


@router.get("/knowledge/platform", response_model=KnowledgeBaseResponse)
async def admin_platform_knowledge_base(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeBaseResponse:
    return await get_platform_knowledge_base(db)


@router.get("/knowledge/platform/documents", response_model=list[KnowledgeDocumentResponse])
async def admin_platform_knowledge_documents(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeDocumentResponse]:
    return await get_platform_documents(db)


@router.post("/knowledge/platform/documents", response_model=KnowledgeDocumentResponse)
async def admin_upload_platform_knowledge_document(
    file: UploadFile = File(...),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    publisher: KnowledgeTaskPublisher = Depends(get_knowledge_task_publisher),
) -> KnowledgeDocumentResponse:
    return await upload_platform_document(db, file, publisher)


@router.put("/knowledge/platform/documents/{document_id}", response_model=KnowledgeDocumentResponse)
async def admin_replace_platform_knowledge_document(
    document_id: int,
    file: UploadFile = File(...),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    publisher: KnowledgeTaskPublisher = Depends(get_knowledge_task_publisher),
) -> KnowledgeDocumentResponse:
    return await replace_platform_document(db, document_id, file, publisher)


@router.post("/knowledge/platform/documents/{document_id}/reindex", response_model=KnowledgeDocumentResponse)
async def admin_reindex_platform_knowledge_document(
    document_id: int,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    publisher: KnowledgeTaskPublisher = Depends(get_knowledge_task_publisher),
) -> KnowledgeDocumentResponse:
    return await reindex_platform_document(db, document_id, publisher)


@router.delete("/knowledge/platform/documents/{document_id}")
async def admin_delete_platform_knowledge_document(
    document_id: int,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    publisher: KnowledgeTaskPublisher = Depends(get_knowledge_task_publisher),
) -> dict[str, str]:
    await delete_platform_document(db, document_id, publisher)
    return {"message": "Platform document deletion scheduled"}


@router.get("/products/pending")
async def pending_products(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await get_pending_products_for_audit(db, page=page, page_size=page_size, keyword=keyword)


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


@router.post("/products/{product_id}/off-sale")
async def admin_off_sale_product(
    product_id: int,
    payload: AdminReasonRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await update_product_audit_status(
        db,
        product_id,
        ProductStatus.OFF_SHELF.value,
        payload.reason,
        commit=False,
    )
    await write_audit_log(
        db,
        target_type="product",
        target_id=product_id,
        action="off_sale",
        result=ProductStatus.OFF_SHELF.value,
        operator_id=admin.id,
        reason=payload.reason,
    )
    await db.commit()
    return {"message": "Product off sale"}


@router.get("/reports")
async def reports(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    keyword: str | None = None,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await list_reports(db, max(page, 1), min(max(page_size, 1), 100), status=status, keyword=keyword)


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
