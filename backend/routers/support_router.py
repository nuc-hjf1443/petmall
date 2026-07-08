from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_db, require_admin
from models.user import User
from schemas.support_schema import (
    SupportConversationListResponse,
    SupportConversationResponse,
    SupportMessageCreate,
    SupportStatusUpdate,
)
from services.support_service import (
    get_or_create_adoption_conversation,
    get_or_create_merchant_conversation,
    get_or_create_platform_conversation,
    get_user_conversation,
    list_admin_support_conversations,
    list_adoption_conversations_for_publisher,
    list_merchant_support_conversations,
    list_user_conversations,
    send_admin_message,
    send_merchant_message,
    send_user_message,
    transfer_merchant_conversation_to_platform,
    update_admin_conversation_status,
    update_merchant_conversation_status,
)


router = APIRouter(tags=["support"])


StatusQuery = Annotated[str | None, Query(pattern="^(pending|resolved)$")]


@router.get("/support/conversations", response_model=SupportConversationListResponse)
async def my_support_conversations(
    status: StatusQuery = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupportConversationListResponse:
    return await list_user_conversations(db, current_user, status=status, page=page, page_size=page_size)


@router.post("/support/platform", response_model=SupportConversationResponse)
async def platform_support_conversation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupportConversationResponse:
    return await get_or_create_platform_conversation(db, current_user)


@router.post("/support/products/{product_id}/merchant", response_model=SupportConversationResponse)
async def merchant_support_conversation(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupportConversationResponse:
    return await get_or_create_merchant_conversation(db, current_user, product_id)


@router.get("/support/adoptions/published", response_model=SupportConversationListResponse)
async def published_adoption_support_conversations(
    status: StatusQuery = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupportConversationListResponse:
    return await list_adoption_conversations_for_publisher(
        db,
        current_user,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.post("/support/adoptions/{adoption_id}", response_model=SupportConversationResponse)
async def adoption_support_conversation(
    adoption_id: int,
    application_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupportConversationResponse:
    return await get_or_create_adoption_conversation(db, current_user, adoption_id, application_id)


@router.get("/support/conversations/{conversation_id}", response_model=SupportConversationResponse)
async def support_conversation_detail(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupportConversationResponse:
    return await get_user_conversation(db, current_user, conversation_id)


@router.post("/support/conversations/{conversation_id}/messages", response_model=SupportConversationResponse)
async def send_support_message(
    conversation_id: int,
    payload: SupportMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupportConversationResponse:
    return await send_user_message(db, current_user, conversation_id, payload)


@router.get("/merchants/me/support/conversations", response_model=SupportConversationListResponse)
async def merchant_support_conversations(
    status: StatusQuery = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupportConversationListResponse:
    return await list_merchant_support_conversations(db, current_user, status=status, page=page, page_size=page_size)


@router.post("/merchants/me/support/conversations/{conversation_id}/messages", response_model=SupportConversationResponse)
async def send_merchant_support_message_api(
    conversation_id: int,
    payload: SupportMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupportConversationResponse:
    return await send_merchant_message(db, current_user, conversation_id, payload)


@router.put("/merchants/me/support/conversations/{conversation_id}/status", response_model=SupportConversationResponse)
async def update_merchant_support_status(
    conversation_id: int,
    payload: SupportStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupportConversationResponse:
    return await update_merchant_conversation_status(db, current_user, conversation_id, payload.status)


@router.post("/merchants/me/support/conversations/{conversation_id}/transfer", response_model=SupportConversationResponse)
async def transfer_merchant_support(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupportConversationResponse:
    return await transfer_merchant_conversation_to_platform(db, current_user, conversation_id)


@router.get("/admin/support/conversations", response_model=SupportConversationListResponse)
async def admin_support_conversations(
    status: StatusQuery = None,
    page: int = 1,
    page_size: int = 20,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> SupportConversationListResponse:
    return await list_admin_support_conversations(db, status=status, page=page, page_size=page_size)


@router.post("/admin/support/conversations/{conversation_id}/messages", response_model=SupportConversationResponse)
async def send_admin_support_message_api(
    conversation_id: int,
    payload: SupportMessageCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> SupportConversationResponse:
    return await send_admin_message(db, admin, conversation_id, payload)


@router.put("/admin/support/conversations/{conversation_id}/status", response_model=SupportConversationResponse)
async def update_admin_support_status(
    conversation_id: int,
    payload: SupportStatusUpdate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> SupportConversationResponse:
    return await update_admin_conversation_status(db, conversation_id, payload.status)
