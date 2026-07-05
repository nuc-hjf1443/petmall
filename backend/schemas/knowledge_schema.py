from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)


class KnowledgeBaseResponse(BaseModel):
    id: int
    name: str
    scope: str
    created_at: datetime


class KnowledgeDocumentResponse(BaseModel):
    id: int
    knowledge_base_id: int
    file_name: str
    file_type: str
    source_type: str
    pet_id: int | None
    parse_status: str
    chunk_count: int
    index_version: int
    error_message: str | None
    created_at: datetime


class GeneratedPetRequest(BaseModel):
    pet_id: int = Field(..., gt=0)


class GeneratedPreviewResponse(BaseModel):
    pet_id: int
    snapshot: dict[str, Any]
    content: str
