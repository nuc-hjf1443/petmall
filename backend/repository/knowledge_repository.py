from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.knowledge import KnowledgeBase, KnowledgeChunk, KnowledgeDocument, KnowledgeTask


async def get_private_kb(db: AsyncSession, kb_id: int, user_id: int) -> KnowledgeBase | None:
    return (await db.execute(select(KnowledgeBase).where(
        KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id, KnowledgeBase.scope == "private"
    ))).scalar_one_or_none()


async def list_private_kbs(db: AsyncSession, user_id: int) -> list[KnowledgeBase]:
    return list((await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.user_id == user_id, KnowledgeBase.scope == "private")
        .order_by(KnowledgeBase.created_at.desc())
    )).scalars())


async def get_platform_kb(db: AsyncSession) -> KnowledgeBase | None:
    return (await db.execute(
        select(KnowledgeBase)
        .where(KnowledgeBase.scope == "platform")
        .order_by(KnowledgeBase.id)
        .limit(1)
    )).scalar_one_or_none()


async def get_private_document(
    db: AsyncSession, document_id: int, kb_id: int, user_id: int, lock: bool = False
) -> KnowledgeDocument | None:
    statement = select(KnowledgeDocument).where(
        KnowledgeDocument.id == document_id,
        KnowledgeDocument.knowledge_base_id == kb_id,
        KnowledgeDocument.user_id == user_id,
    )
    if lock:
        statement = statement.with_for_update()
    return (await db.execute(statement)).scalar_one_or_none()


async def get_platform_document(
    db: AsyncSession, document_id: int, lock: bool = False
) -> KnowledgeDocument | None:
    statement = (
        select(KnowledgeDocument)
        .join(KnowledgeBase, KnowledgeBase.id == KnowledgeDocument.knowledge_base_id)
        .where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.user_id.is_(None),
            KnowledgeBase.scope == "platform",
        )
    )
    if lock:
        statement = statement.with_for_update()
    return (await db.execute(statement)).scalar_one_or_none()


async def list_documents(db: AsyncSession, kb_id: int, user_id: int) -> list[KnowledgeDocument]:
    return list((await db.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.knowledge_base_id == kb_id, KnowledgeDocument.user_id == user_id
        ).order_by(KnowledgeDocument.created_at.desc())
    )).scalars())


async def list_platform_documents(db: AsyncSession, kb_id: int) -> list[KnowledgeDocument]:
    return list((await db.execute(
        select(KnowledgeDocument)
        .where(
            KnowledgeDocument.knowledge_base_id == kb_id,
            KnowledgeDocument.user_id.is_(None),
        )
        .order_by(KnowledgeDocument.created_at.desc())
    )).scalars())


async def get_task(db: AsyncSession, task_id: int, lock: bool = False) -> KnowledgeTask | None:
    statement = select(KnowledgeTask).where(KnowledgeTask.id == task_id)
    if lock:
        statement = statement.with_for_update()
    return (await db.execute(statement)).scalar_one_or_none()


async def delete_document_chunks(db: AsyncSession, document_id: int) -> None:
    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id))
