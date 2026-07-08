from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.support import SupportConversation, SupportMessage


def conversation_load_options():
    return (selectinload(SupportConversation.messages),)


async def get_conversation(db: AsyncSession, conversation_id: int) -> SupportConversation | None:
    result = await db.execute(
        select(SupportConversation)
        .options(*conversation_load_options())
        .where(SupportConversation.id == conversation_id)
    )
    return result.scalar_one_or_none()


async def find_platform_conversation(db: AsyncSession, user_id: int) -> SupportConversation | None:
    result = await db.execute(
        select(SupportConversation)
        .options(*conversation_load_options())
        .where(
            SupportConversation.user_id == user_id,
            SupportConversation.type == "platform",
        )
        .order_by(SupportConversation.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def find_merchant_conversation(
    db: AsyncSession,
    user_id: int,
    merchant_id: int,
) -> SupportConversation | None:
    result = await db.execute(
        select(SupportConversation)
        .options(*conversation_load_options())
        .where(
            SupportConversation.user_id == user_id,
            SupportConversation.merchant_id == merchant_id,
            SupportConversation.type == "merchant",
        )
        .order_by(SupportConversation.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def find_adoption_conversation(
    db: AsyncSession,
    adoption_pet_id: int,
    adoption_application_id: int | None,
    user_id: int,
) -> SupportConversation | None:
    filters = [
        SupportConversation.type == "adoption",
        SupportConversation.adoption_pet_id == adoption_pet_id,
        SupportConversation.user_id == user_id,
    ]
    if adoption_application_id is None:
        filters.append(SupportConversation.adoption_application_id.is_(None))
    else:
        filters.append(SupportConversation.adoption_application_id == adoption_application_id)
    result = await db.execute(
        select(SupportConversation)
        .options(*conversation_load_options())
        .where(*filters)
        .order_by(SupportConversation.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_conversations(
    db: AsyncSession,
    filters: list,
    *,
    page: int,
    page_size: int,
) -> tuple[list[SupportConversation], int]:
    total = int((await db.scalar(select(func.count(SupportConversation.id)).where(*filters))) or 0)
    result = await db.execute(
        select(SupportConversation)
        .options(*conversation_load_options())
        .where(*filters)
        .order_by(SupportConversation.last_message_at.desc(), SupportConversation.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().unique().all()), total


async def add_message(
    db: AsyncSession,
    conversation: SupportConversation,
    sender_id: int,
    content: str,
) -> SupportMessage:
    message = SupportMessage(conversation_id=conversation.id, sender_id=sender_id, content=content)
    db.add(message)
    conversation.status = "pending"
    await db.flush()
    conversation.last_message_at = message.created_at
    return message
