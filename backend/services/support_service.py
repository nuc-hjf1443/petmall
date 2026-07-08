from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import bad_request, forbidden, not_found
from models.adoption import AdoptionApplication, AdoptionPet
from models.merchant import Merchant
from models.product import Product
from models.support import SupportConversation, SupportConversationStatus, SupportConversationType, SupportMessage
from models.user import User
from repository.support_repository import (
    add_message,
    find_adoption_conversation,
    find_merchant_conversation,
    find_platform_conversation,
    get_conversation,
    list_conversations,
)
from schemas.support_schema import (
    SupportConversationListResponse,
    SupportConversationResponse,
    SupportMessageCreate,
    SupportMessageResponse,
)
from services.merchant_service import get_my_merchant


def _safe_page(page: int) -> int:
    return max(page, 1)


def _safe_page_size(page_size: int) -> int:
    return min(max(page_size, 1), 100)


async def _conversation_response(db: AsyncSession, conversation: SupportConversation) -> SupportConversationResponse:
    merchant_name = None
    adoption_pet_name = None
    if conversation.merchant_id:
        merchant = await db.get(Merchant, conversation.merchant_id)
        merchant_name = merchant.shop_name if merchant else None
    if conversation.adoption_pet_id:
        adoption = await db.get(AdoptionPet, conversation.adoption_pet_id)
        adoption_pet_name = adoption.name if adoption else None
    messages = (
        await db.execute(
            select(SupportMessage)
            .where(SupportMessage.conversation_id == conversation.id)
            .order_by(SupportMessage.created_at, SupportMessage.id)
        )
    ).scalars().all()
    return SupportConversationResponse(
        id=conversation.id,
        type=conversation.type,
        status=conversation.status,
        user_id=conversation.user_id,
        merchant_id=conversation.merchant_id,
        merchant_name=merchant_name,
        adoption_pet_id=conversation.adoption_pet_id,
        adoption_pet_name=adoption_pet_name,
        adoption_application_id=conversation.adoption_application_id,
        assigned_to_platform=conversation.assigned_to_platform,
        last_message_at=conversation.last_message_at,
        created_at=conversation.created_at,
        messages=[
            SupportMessageResponse.model_validate(message, from_attributes=True)
            for message in messages
        ],
    )


async def _page_response(
    db: AsyncSession,
    conversations: list[SupportConversation],
    total: int,
    page: int,
    page_size: int,
) -> SupportConversationListResponse:
    return SupportConversationListResponse(
        items=[await _conversation_response(db, conversation) for conversation in conversations],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_or_create_platform_conversation(
    db: AsyncSession,
    user: User,
) -> SupportConversationResponse:
    conversation = await find_platform_conversation(db, user.id)
    if conversation is None:
        conversation = SupportConversation(
            type=SupportConversationType.PLATFORM.value,
            user_id=user.id,
            assigned_to_platform=True,
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        conversation = await get_conversation(db, conversation.id)
    return await _conversation_response(db, conversation)


async def get_or_create_merchant_conversation(
    db: AsyncSession,
    user: User,
    product_id: int,
) -> SupportConversationResponse:
    product = await db.get(Product, product_id)
    if product is None or product.status != "on_sale":
        raise not_found("Product not found")
    merchant = await db.get(Merchant, product.merchant_id)
    if merchant is None or merchant.status != "approved":
        raise not_found("Merchant not found")
    if merchant.owner_user_id == user.id:
        raise bad_request("不能联系自己的店铺客服")
    conversation = await find_merchant_conversation(db, user.id, merchant.id)
    if conversation is None:
        conversation = SupportConversation(
            type=SupportConversationType.MERCHANT.value,
            user_id=user.id,
            merchant_id=merchant.id,
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        conversation = await get_conversation(db, conversation.id)
    return await _conversation_response(db, conversation)


async def get_or_create_adoption_conversation(
    db: AsyncSession,
    user: User,
    adoption_id: int,
    application_id: int | None = None,
) -> SupportConversationResponse:
    adoption = await db.get(AdoptionPet, adoption_id)
    if adoption is None or adoption.is_deleted:
        raise not_found("Adoption pet not found")
    if adoption.publisher_id == user.id:
        raise bad_request("不能联系自己发布的领养信息")
    application = None
    if application_id is not None:
        application = await db.get(AdoptionApplication, application_id)
        if (
            application is None
            or application.adoption_pet_id != adoption.id
            or application.applicant_id != user.id
        ):
            raise forbidden("Adoption application is not accessible")
    conversation = await find_adoption_conversation(
        db,
        adoption.id,
        application.id if application else None,
        user.id,
    )
    if conversation is None:
        conversation = SupportConversation(
            type=SupportConversationType.ADOPTION.value,
            user_id=user.id,
            adoption_pet_id=adoption.id,
            adoption_application_id=application.id if application else None,
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        conversation = await get_conversation(db, conversation.id)
    return await _conversation_response(db, conversation)


async def _ensure_user_access(db: AsyncSession, user: User, conversation: SupportConversation) -> None:
    if user.is_admin:
        return
    if conversation.user_id == user.id:
        return
    if conversation.type == SupportConversationType.ADOPTION.value and conversation.adoption_pet_id:
        adoption = await db.get(AdoptionPet, conversation.adoption_pet_id)
        if adoption is not None and adoption.publisher_id == user.id:
            return
    if conversation.type == SupportConversationType.MERCHANT.value and conversation.merchant_id:
        merchant = await db.get(Merchant, conversation.merchant_id)
        if merchant is not None and merchant.owner_user_id == user.id:
            return
    raise forbidden("Conversation is not accessible")


async def get_user_conversation(
    db: AsyncSession,
    user: User,
    conversation_id: int,
) -> SupportConversationResponse:
    conversation = await get_conversation(db, conversation_id)
    if conversation is None:
        raise not_found("Conversation not found")
    await _ensure_user_access(db, user, conversation)
    return await _conversation_response(db, conversation)


async def send_user_message(
    db: AsyncSession,
    user: User,
    conversation_id: int,
    payload: SupportMessageCreate,
) -> SupportConversationResponse:
    conversation = await get_conversation(db, conversation_id)
    if conversation is None:
        raise not_found("Conversation not found")
    await _ensure_user_access(db, user, conversation)
    content = payload.content.strip()
    if not content:
        raise bad_request("Message content is required")
    await add_message(db, conversation, user.id, content)
    await db.commit()
    refreshed = await get_conversation(db, conversation_id)
    return await _conversation_response(db, refreshed)


async def list_user_conversations(
    db: AsyncSession,
    user: User,
    *,
    status: str | None,
    page: int,
    page_size: int,
) -> SupportConversationListResponse:
    page = _safe_page(page)
    page_size = _safe_page_size(page_size)
    filters = [SupportConversation.user_id == user.id]
    if status:
        filters.append(SupportConversation.status == status)
    rows, total = await list_conversations(db, filters, page=page, page_size=page_size)
    return await _page_response(db, rows, total, page, page_size)


async def list_adoption_conversations_for_publisher(
    db: AsyncSession,
    user: User,
    *,
    status: str | None,
    page: int,
    page_size: int,
) -> SupportConversationListResponse:
    page = _safe_page(page)
    page_size = _safe_page_size(page_size)
    publisher_pet_ids = select(AdoptionPet.id).where(AdoptionPet.publisher_id == user.id)
    filters = [
        SupportConversation.type == SupportConversationType.ADOPTION.value,
        SupportConversation.adoption_pet_id.in_(publisher_pet_ids),
    ]
    if status:
        filters.append(SupportConversation.status == status)
    rows, total = await list_conversations(db, filters, page=page, page_size=page_size)
    return await _page_response(db, rows, total, page, page_size)


async def list_merchant_support_conversations(
    db: AsyncSession,
    user: User,
    *,
    status: str | None,
    page: int,
    page_size: int,
) -> SupportConversationListResponse:
    merchant = await get_my_merchant(db, user.id)
    page = _safe_page(page)
    page_size = _safe_page_size(page_size)
    filters = [
        SupportConversation.type == SupportConversationType.MERCHANT.value,
        SupportConversation.merchant_id == merchant.id,
    ]
    if status:
        filters.append(SupportConversation.status == status)
    rows, total = await list_conversations(db, filters, page=page, page_size=page_size)
    return await _page_response(db, rows, total, page, page_size)


async def _ensure_merchant_conversation(
    db: AsyncSession,
    user: User,
    conversation_id: int,
) -> SupportConversation:
    merchant = await get_my_merchant(db, user.id)
    conversation = await get_conversation(db, conversation_id)
    if (
        conversation is None
        or conversation.type != SupportConversationType.MERCHANT.value
        or conversation.merchant_id != merchant.id
    ):
        raise not_found("Conversation not found")
    return conversation


async def send_merchant_message(
    db: AsyncSession,
    user: User,
    conversation_id: int,
    payload: SupportMessageCreate,
) -> SupportConversationResponse:
    conversation = await _ensure_merchant_conversation(db, user, conversation_id)
    content = payload.content.strip()
    if not content:
        raise bad_request("Message content is required")
    await add_message(db, conversation, user.id, content)
    await db.commit()
    return await _conversation_response(db, await get_conversation(db, conversation_id))


async def update_merchant_conversation_status(
    db: AsyncSession,
    user: User,
    conversation_id: int,
    status: str,
) -> SupportConversationResponse:
    conversation = await _ensure_merchant_conversation(db, user, conversation_id)
    conversation.status = status
    await db.commit()
    return await _conversation_response(db, await get_conversation(db, conversation_id))


async def transfer_merchant_conversation_to_platform(
    db: AsyncSession,
    user: User,
    conversation_id: int,
) -> SupportConversationResponse:
    conversation = await _ensure_merchant_conversation(db, user, conversation_id)
    conversation.assigned_to_platform = True
    conversation.status = SupportConversationStatus.PENDING.value
    await db.commit()
    return await _conversation_response(db, await get_conversation(db, conversation_id))


async def list_admin_support_conversations(
    db: AsyncSession,
    *,
    status: str | None,
    page: int,
    page_size: int,
) -> SupportConversationListResponse:
    page = _safe_page(page)
    page_size = _safe_page_size(page_size)
    filters = [
        or_(
            SupportConversation.type == SupportConversationType.PLATFORM.value,
            SupportConversation.assigned_to_platform.is_(True),
        )
    ]
    if status:
        filters.append(SupportConversation.status == status)
    rows, total = await list_conversations(db, filters, page=page, page_size=page_size)
    return await _page_response(db, rows, total, page, page_size)


async def _ensure_admin_conversation(db: AsyncSession, conversation_id: int) -> SupportConversation:
    conversation = await get_conversation(db, conversation_id)
    if conversation is None:
        raise not_found("Conversation not found")
    if conversation.type != SupportConversationType.PLATFORM.value and not conversation.assigned_to_platform:
        raise forbidden("Conversation is not assigned to platform")
    return conversation


async def send_admin_message(
    db: AsyncSession,
    admin: User,
    conversation_id: int,
    payload: SupportMessageCreate,
) -> SupportConversationResponse:
    conversation = await _ensure_admin_conversation(db, conversation_id)
    content = payload.content.strip()
    if not content:
        raise bad_request("Message content is required")
    await add_message(db, conversation, admin.id, content)
    await db.commit()
    return await _conversation_response(db, await get_conversation(db, conversation_id))


async def update_admin_conversation_status(
    db: AsyncSession,
    conversation_id: int,
    status: str,
) -> SupportConversationResponse:
    conversation = await _ensure_admin_conversation(db, conversation_id)
    conversation.status = status
    await db.commit()
    return await _conversation_response(db, await get_conversation(db, conversation_id))
