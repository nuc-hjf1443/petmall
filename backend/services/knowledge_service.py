from datetime import timedelta
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import bad_request, conflict, not_found
from core.knowledge_queue import KnowledgeTaskPublisher
from core.rag_service import VectorService
from models.knowledge import (
    DocumentStatus, KnowledgeBase, KnowledgeChunk, KnowledgeDocument, KnowledgeTask
)
from models.base import utc_now
from repository.knowledge_repository import (
    delete_document_chunks, get_platform_document, get_platform_kb,
    get_private_document, get_private_kb, get_task, list_documents,
    list_platform_documents, list_private_kbs,
)
from schemas.knowledge_schema import (
    GeneratedPreviewResponse, KnowledgeBaseCreate, KnowledgeBaseResponse, KnowledgeDocumentResponse
)
from services.document_parse_service import parse_document, split_text
from settings.config import get_settings


ALLOWED_DOCUMENTS = {
    "text/plain": "txt",
    "application/pdf": "pdf",
}


class PetProfileDocumentAdapter(Protocol):
    async def generate(self, db: AsyncSession, user_id: int, pet_id: int) -> tuple[dict[str, Any], str]: ...


class UnavailablePetProfileDocumentAdapter:
    async def generate(self, db: AsyncSession, user_id: int, pet_id: int) -> tuple[dict[str, Any], str]:
        raise conflict("Pet profile document integration is unavailable")


def get_pet_profile_document_adapter() -> PetProfileDocumentAdapter:
    from services.profile_document_service import RealPetProfileDocumentAdapter

    return RealPetProfileDocumentAdapter()


def _kb_response(kb: KnowledgeBase) -> KnowledgeBaseResponse:
    return KnowledgeBaseResponse.model_validate(kb, from_attributes=True)


def _doc_response(doc: KnowledgeDocument) -> KnowledgeDocumentResponse:
    return KnowledgeDocumentResponse.model_validate(doc, from_attributes=True)


def _platform_knowledge_dir() -> Path:
    directory = get_settings().private_asset_path / "knowledge" / "platform"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


async def _ensure_platform_kb(db: AsyncSession) -> KnowledgeBase:
    knowledge_base = await get_platform_kb(db)
    if knowledge_base is None:
        knowledge_base = KnowledgeBase(user_id=None, name="Platform knowledge", scope="platform")
        db.add(knowledge_base)
        await db.flush()
    return knowledge_base


async def _store_upload_file(upload: UploadFile, directory: Path) -> tuple[str, str, Path]:
    file_type = ALLOWED_DOCUMENTS.get(upload.content_type or "")
    extension = Path(upload.filename or "").suffix.lower()
    if file_type is None or extension != f".{file_type}":
        raise bad_request("Only matching TXT and PDF files are supported")
    limit = get_settings().max_upload_size_mb * 1024 * 1024
    data = await upload.read(limit + 1)
    if not data or len(data) > limit:
        raise bad_request("Document is empty or too large")
    path = directory / f"{uuid4().hex}.{file_type}"
    path.write_bytes(data)
    return Path(upload.filename or "document").name, file_type, path


async def create_knowledge_base(db: AsyncSession, user_id: int, payload: KnowledgeBaseCreate):
    kb = KnowledgeBase(user_id=user_id, name=payload.name.strip(), scope="private")
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return _kb_response(kb)


async def get_knowledge_bases(db: AsyncSession, user_id: int):
    return [_kb_response(kb) for kb in await list_private_kbs(db, user_id)]


async def get_knowledge_base(db: AsyncSession, user_id: int, kb_id: int):
    kb = await get_private_kb(db, kb_id, user_id)
    if kb is None:
        raise not_found("Knowledge base not found")
    return _kb_response(kb)


async def _new_task(
    db: AsyncSession, document: KnowledgeDocument, task_type: str, publisher: KnowledgeTaskPublisher
) -> None:
    task = KnowledgeTask(
        task_key=f"{task_type}:{document.id}:v{document.index_version}",
        task_type=task_type,
        document_id=document.id,
        knowledge_base_id=document.knowledge_base_id,
        user_id=document.user_id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    try:
        await publisher.publish(task.id)
    except Exception as exc:
        task.status = "failed"
        task.error_message = f"Queue publish failed: {exc}"[:2000]
        document.parse_status = DocumentStatus.FAILED.value
        document.error_message = task.error_message
        await db.commit()
        raise


async def upload_document(
    db: AsyncSession, user_id: int, kb_id: int, upload: UploadFile, publisher: KnowledgeTaskPublisher
):
    if await get_private_kb(db, kb_id, user_id) is None:
        raise not_found("Knowledge base not found")
    directory = get_settings().private_asset_path / "knowledge" / str(user_id)
    directory.mkdir(parents=True, exist_ok=True)
    file_name, file_type, path = await _store_upload_file(upload, directory)
    document = KnowledgeDocument(
        knowledge_base_id=kb_id, user_id=user_id, file_name=file_name,
        file_type=file_type, file_path=str(path), source_type="upload",
        parse_status=DocumentStatus.PENDING.value,
    )
    try:
        db.add(document)
        await db.commit()
        await db.refresh(document)
        await _new_task(db, document, "index", publisher)
        return _doc_response(document)
    except Exception:
        await db.rollback()
        if document.id is None:
            path.unlink(missing_ok=True)
        raise


async def generated_preview(
    db: AsyncSession, user_id: int, pet_id: int, adapter: PetProfileDocumentAdapter
) -> GeneratedPreviewResponse:
    snapshot, content = await adapter.generate(db, user_id, pet_id)
    return GeneratedPreviewResponse(pet_id=pet_id, snapshot=snapshot, content=content)


async def create_generated_pet_profile_document(
    db: AsyncSession, user_id: int, pet_id: int, kb_id: int,
    publisher: KnowledgeTaskPublisher, adapter: PetProfileDocumentAdapter | None = None,
) -> KnowledgeDocumentResponse:
    if await get_private_kb(db, kb_id, user_id) is None:
        raise not_found("Knowledge base not found")
    snapshot, content = await (adapter or get_pet_profile_document_adapter()).generate(db, user_id, pet_id)
    directory = get_settings().private_asset_path / "knowledge" / str(user_id)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{uuid4().hex}.txt"
    path.write_text(content, encoding="utf-8")
    document = KnowledgeDocument(
        knowledge_base_id=kb_id, user_id=user_id, file_name=f"pet-{pet_id}-profile.txt",
        file_type="txt", file_path=str(path), source_type="generated_pet_profile",
        pet_id=pet_id, source_snapshot=snapshot, parse_status=DocumentStatus.PENDING.value,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    await _new_task(db, document, "index", publisher)
    return _doc_response(document)


async def create_platform_knowledge_document(
    db: AsyncSession,
    *,
    title: str,
    content: str,
    publisher: KnowledgeTaskPublisher,
    knowledge_base_id: int | None = None,
) -> KnowledgeDocumentResponse:
    normalized_title = title.strip()
    normalized_content = content.strip()
    if not normalized_title or not normalized_content:
        raise bad_request("Platform document title and content are required")
    knowledge_base = None
    if knowledge_base_id is not None:
        knowledge_base = await db.get(KnowledgeBase, knowledge_base_id)
        if knowledge_base is None or knowledge_base.scope != "platform":
            raise not_found("Platform knowledge base not found")
    else:
        knowledge_base = (
            await db.execute(
                select(KnowledgeBase)
                .where(KnowledgeBase.scope == "platform")
                .order_by(KnowledgeBase.id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if knowledge_base is None:
            knowledge_base = KnowledgeBase(
                user_id=None, name="Platform knowledge", scope="platform"
            )
            db.add(knowledge_base)
            await db.flush()

    directory = get_settings().private_asset_path / "knowledge" / "platform"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{uuid4().hex}.txt"
    path.write_text(normalized_content, encoding="utf-8")
    document = KnowledgeDocument(
        knowledge_base_id=knowledge_base.id,
        user_id=None,
        file_name=f"{normalized_title[:200]}.txt",
        file_type="txt",
        file_path=str(path),
        source_type="platform",
        parse_status=DocumentStatus.PENDING.value,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    await _new_task(db, document, "index", publisher)
    return _doc_response(document)


async def get_platform_knowledge_base(db: AsyncSession) -> KnowledgeBaseResponse:
    knowledge_base = await _ensure_platform_kb(db)
    await db.commit()
    await db.refresh(knowledge_base)
    return _kb_response(knowledge_base)


async def get_platform_documents(db: AsyncSession) -> list[KnowledgeDocumentResponse]:
    knowledge_base = await _ensure_platform_kb(db)
    await db.commit()
    return [_doc_response(doc) for doc in await list_platform_documents(db, knowledge_base.id)]


async def upload_platform_document(
    db: AsyncSession, upload: UploadFile, publisher: KnowledgeTaskPublisher
) -> KnowledgeDocumentResponse:
    knowledge_base = await _ensure_platform_kb(db)
    file_name, file_type, path = await _store_upload_file(upload, _platform_knowledge_dir())
    document = KnowledgeDocument(
        knowledge_base_id=knowledge_base.id,
        user_id=None,
        file_name=file_name,
        file_type=file_type,
        file_path=str(path),
        source_type="platform_upload",
        parse_status=DocumentStatus.PENDING.value,
    )
    try:
        db.add(document)
        await db.commit()
        await db.refresh(document)
        await _new_task(db, document, "index", publisher)
        return _doc_response(document)
    except Exception:
        await db.rollback()
        if document.id is None:
            path.unlink(missing_ok=True)
        raise


async def replace_platform_document(
    db: AsyncSession, document_id: int, upload: UploadFile, publisher: KnowledgeTaskPublisher
) -> KnowledgeDocumentResponse:
    document = await get_platform_document(db, document_id, lock=True)
    if document is None:
        raise not_found("Platform document not found")
    if document.parse_status in {DocumentStatus.PROCESSING.value, DocumentStatus.DELETING.value}:
        raise conflict("Document is busy")
    file_name, file_type, path = await _store_upload_file(upload, _platform_knowledge_dir())
    old_path = Path(document.file_path)
    try:
        document.file_name = file_name
        document.file_type = file_type
        document.file_path = str(path)
        document.source_type = "platform_upload"
        document.pet_id = None
        document.source_snapshot = None
        document.index_version += 1
        document.parse_status = DocumentStatus.PENDING.value
        document.error_message = None
        await db.commit()
        await db.refresh(document)
        await _new_task(db, document, "reindex", publisher)
        old_path.unlink(missing_ok=True)
        return _doc_response(document)
    except Exception:
        await db.rollback()
        path.unlink(missing_ok=True)
        raise


async def reindex_platform_document(
    db: AsyncSession, document_id: int, publisher: KnowledgeTaskPublisher
) -> KnowledgeDocumentResponse:
    document = await get_platform_document(db, document_id, lock=True)
    if document is None:
        raise not_found("Platform document not found")
    if document.parse_status in {DocumentStatus.PROCESSING.value, DocumentStatus.DELETING.value}:
        raise conflict("Document is busy")
    document.index_version += 1
    document.parse_status = DocumentStatus.PENDING.value
    document.error_message = None
    await db.commit()
    await _new_task(db, document, "reindex", publisher)
    return _doc_response(document)


async def delete_platform_document(
    db: AsyncSession, document_id: int, publisher: KnowledgeTaskPublisher
) -> None:
    document = await get_platform_document(db, document_id, lock=True)
    if document is None:
        raise not_found("Platform document not found")
    if document.parse_status == DocumentStatus.DELETING.value:
        return
    document.parse_status = DocumentStatus.DELETING.value
    document.index_version += 1
    await db.commit()
    await _new_task(db, document, "delete", publisher)


async def get_documents(db: AsyncSession, user_id: int, kb_id: int):
    if await get_private_kb(db, kb_id, user_id) is None:
        raise not_found("Knowledge base not found")
    return [_doc_response(doc) for doc in await list_documents(db, kb_id, user_id)]


async def reindex_document(
    db: AsyncSession, user_id: int, kb_id: int, document_id: int, publisher: KnowledgeTaskPublisher
):
    document = await get_private_document(db, document_id, kb_id, user_id, lock=True)
    if document is None:
        raise not_found("Document not found")
    if document.parse_status in {DocumentStatus.PROCESSING.value, DocumentStatus.DELETING.value}:
        raise conflict("Document is busy")
    document.index_version += 1
    document.parse_status = DocumentStatus.PENDING.value
    document.error_message = None
    await db.commit()
    await _new_task(db, document, "reindex", publisher)
    return _doc_response(document)


async def delete_document(
    db: AsyncSession, user_id: int, kb_id: int, document_id: int, publisher: KnowledgeTaskPublisher
) -> None:
    document = await get_private_document(db, document_id, kb_id, user_id, lock=True)
    if document is None:
        raise not_found("Document not found")
    if document.parse_status == DocumentStatus.DELETING.value:
        return
    document.parse_status = DocumentStatus.DELETING.value
    document.index_version += 1
    await db.commit()
    await _new_task(db, document, "delete", publisher)


async def delete_knowledge_base(
    db: AsyncSession, user_id: int, kb_id: int, publisher: KnowledgeTaskPublisher
) -> None:
    kb = await get_private_kb(db, kb_id, user_id)
    if kb is None:
        raise not_found("Knowledge base not found")
    documents = await list_documents(db, kb_id, user_id)
    for document in documents:
        await delete_document(db, user_id, kb_id, document.id, publisher)
    if not documents:
        await db.delete(kb)
        await db.commit()


async def process_knowledge_task(db: AsyncSession, task_id: int, vectors: VectorService) -> None:
    now = utc_now()
    stale_before = now - timedelta(seconds=get_settings().knowledge_task_lease_seconds)
    claim = await db.execute(
        update(KnowledgeTask)
        .where(
            KnowledgeTask.id == task_id,
            or_(
                KnowledgeTask.status.in_(["pending", "failed"]),
                and_(
                    KnowledgeTask.status == "processing",
                    KnowledgeTask.updated_at < stale_before,
                ),
            ),
        )
        .values(status="processing", error_message=None, updated_at=now)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    if claim.rowcount != 1:
        return
    task = await get_task(db, task_id)
    if task is None:
        return
    document = await db.get(KnowledgeDocument, task.document_id)
    if (
        document is None
        or document.user_id != task.user_id
        or document.knowledge_base_id != task.knowledge_base_id
    ):
        task.status = "failed"
        task.error_message = "Task ownership mismatch"
        await db.commit()
        return
    try:
        if task.task_type == "delete":
            await vectors.delete_document(document.id)
            await delete_document_chunks(db, document.id)
            Path(document.file_path).unlink(missing_ok=True)
            knowledge_base_id = document.knowledge_base_id
            await db.execute(delete(KnowledgeTask).where(KnowledgeTask.document_id == document.id))
            await db.delete(document)
            await db.flush()
            remaining = int((await db.scalar(
                select(func.count(KnowledgeDocument.id)).where(
                    KnowledgeDocument.knowledge_base_id == knowledge_base_id
                )
            )) or 0)
            if remaining == 0:
                knowledge_base = await db.get(KnowledgeBase, knowledge_base_id)
                if knowledge_base is not None:
                    await db.delete(knowledge_base)
        else:
            document.parse_status = DocumentStatus.PROCESSING.value
            await db.commit()
            await vectors.delete_document(document.id)
            await delete_document_chunks(db, document.id)
            text = parse_document(Path(document.file_path), document.file_type)
            settings = get_settings()
            chunks = split_text(text, settings.rag_chunk_size, settings.rag_chunk_overlap)
            vector_ids = [f"doc:{document.id}:v{document.index_version}:chunk:{i}" for i in range(len(chunks))]
            metadata = [{
                "user_id": document.user_id or 0, "knowledge_base_id": document.knowledge_base_id,
                "document_id": document.id, "chunk_index": i,
                "source_type": document.source_type, "scope": "private" if document.user_id else "platform",
            } for i in range(len(chunks))]
            await vectors.upsert(vector_ids, chunks, metadata)
            for i, (vector_id, content) in enumerate(zip(vector_ids, chunks)):
                db.add(KnowledgeChunk(
                    knowledge_base_id=document.knowledge_base_id, document_id=document.id,
                    user_id=document.user_id, index_version=document.index_version,
                    chunk_index=i, vector_id=vector_id, content=content,
                ))
            document.chunk_count = len(chunks)
            document.parse_status = DocumentStatus.PARSED.value
            document.error_message = None
        if task.task_type != "delete":
            task.status = "completed"
            task.error_message = None
        await db.commit()
    except Exception as exc:
        await db.rollback()
        task = await get_task(db, task_id)
        document = await db.get(KnowledgeDocument, task.document_id) if task else None
        if task:
            task.status = "failed"
            task.error_message = str(exc)[:2000]
        if document:
            document.parse_status = DocumentStatus.FAILED.value
            document.error_message = str(exc)[:2000]
        await db.commit()
        raise
