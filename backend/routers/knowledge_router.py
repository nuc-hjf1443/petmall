from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_db
from core.knowledge_queue import KnowledgeTaskPublisher, get_knowledge_task_publisher
from models.user import User
from schemas.knowledge_schema import (
    GeneratedPetRequest, GeneratedPreviewResponse, KnowledgeBaseCreate,
    KnowledgeBaseResponse, KnowledgeDocumentResponse,
)
from services.knowledge_service import (
    PetProfileDocumentAdapter, create_generated_pet_profile_document, create_knowledge_base,
    delete_document, delete_knowledge_base, generated_preview, get_documents,
    get_knowledge_base, get_knowledge_bases, get_pet_profile_document_adapter,
    reindex_document, upload_document,
)


router = APIRouter(prefix="/knowledge-bases", tags=["knowledge"])


@router.post("", response_model=KnowledgeBaseResponse)
async def create_kb(payload: KnowledgeBaseCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await create_knowledge_base(db, user.id, payload)


@router.get("", response_model=list[KnowledgeBaseResponse])
async def list_kbs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await get_knowledge_bases(db, user.id)


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def kb_detail(kb_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await get_knowledge_base(db, user.id, kb_id)


@router.delete("/{kb_id}")
async def remove_kb(
    kb_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
    publisher: KnowledgeTaskPublisher = Depends(get_knowledge_task_publisher),
):
    await delete_knowledge_base(db, user.id, kb_id, publisher)
    return {"message": "Knowledge base deletion scheduled"}


@router.post("/{kb_id}/documents", response_model=KnowledgeDocumentResponse)
async def upload(
    kb_id: int, file: UploadFile = File(...), user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    publisher: KnowledgeTaskPublisher = Depends(get_knowledge_task_publisher),
):
    return await upload_document(db, user.id, kb_id, file, publisher)


@router.post("/{kb_id}/documents/generated-preview", response_model=GeneratedPreviewResponse)
async def preview(
    kb_id: int, payload: GeneratedPetRequest, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    adapter: PetProfileDocumentAdapter = Depends(get_pet_profile_document_adapter),
):
    await get_knowledge_base(db, user.id, kb_id)
    return await generated_preview(db, user.id, payload.pet_id, adapter)


@router.post("/{kb_id}/documents/generate-from-pet", response_model=KnowledgeDocumentResponse)
async def generate(
    kb_id: int, payload: GeneratedPetRequest, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    publisher: KnowledgeTaskPublisher = Depends(get_knowledge_task_publisher),
    adapter: PetProfileDocumentAdapter = Depends(get_pet_profile_document_adapter),
):
    return await create_generated_pet_profile_document(
        db, user.id, payload.pet_id, kb_id, publisher, adapter
    )


@router.get("/{kb_id}/documents", response_model=list[KnowledgeDocumentResponse])
async def documents(kb_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await get_documents(db, user.id, kb_id)


@router.delete("/{kb_id}/documents/{document_id}")
async def remove_document(
    kb_id: int, document_id: int, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    publisher: KnowledgeTaskPublisher = Depends(get_knowledge_task_publisher),
):
    await delete_document(db, user.id, kb_id, document_id, publisher)
    return {"message": "Document deletion scheduled"}


@router.post("/{kb_id}/documents/{document_id}/reindex", response_model=KnowledgeDocumentResponse)
async def reindex(
    kb_id: int, document_id: int, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    publisher: KnowledgeTaskPublisher = Depends(get_knowledge_task_publisher),
):
    return await reindex_document(db, user.id, kb_id, document_id, publisher)
