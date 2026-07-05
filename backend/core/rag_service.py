from typing import Any, Protocol

import chromadb
import ollama
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.knowledge import KnowledgeBase, RagRetrievalLog
from settings.config import get_settings


class VectorService(Protocol):
    async def upsert(self, ids: list[str], texts: list[str], metadata: list[dict[str, Any]]) -> None: ...
    async def delete_document(self, document_id: int) -> None: ...
    async def query(self, query: str, where: dict[str, Any], top_k: int) -> list[dict[str, Any]]: ...


class ChromaOllamaVectorService:
    def __init__(self) -> None:
        settings = get_settings()
        self.collection = chromadb.PersistentClient(
            path=str(settings.vector_store_path)
        ).get_or_create_collection(settings.chroma_collection)
        self.ollama = ollama.AsyncClient(host=settings.ollama_base_url)
        self.model = settings.ollama_embed_model

    async def _embeddings(self, texts: list[str]) -> list[list[float]]:
        response = await self.ollama.embed(model=self.model, input=texts)
        return response["embeddings"]

    async def upsert(self, ids: list[str], texts: list[str], metadata: list[dict[str, Any]]) -> None:
        self.collection.upsert(
            ids=ids, documents=texts, metadatas=metadata, embeddings=await self._embeddings(texts)
        )

    async def delete_document(self, document_id: int) -> None:
        self.collection.delete(where={"document_id": document_id})

    async def query(self, query: str, where: dict[str, Any], top_k: int) -> list[dict[str, Any]]:
        result = self.collection.query(
            query_embeddings=(await self._embeddings([query])),
            where=where,
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        return [
            {"content": text, "metadata": metadata, "score": 1 / (1 + distance)}
            for text, metadata, distance in zip(
                result["documents"][0], result["metadatas"][0], result["distances"][0]
            )
        ]


def get_vector_service() -> VectorService:
    return ChromaOllamaVectorService()


async def retrieve_private_knowledge(
    db: AsyncSession, user_id: int, query: str, top_k: int = 5,
    vector_service: VectorService | None = None, caller: str = "service"
) -> list[dict]:
    service = vector_service or get_vector_service()
    results = await service.query(
        query, {"$and": [{"user_id": user_id}, {"scope": "private"}]}, max(1, min(top_k, 20))
    )
    db.add(RagRetrievalLog(
        user_id=user_id, query_text=query[:500], caller=caller,
        results=[{"document_id": r["metadata"].get("document_id"), "score": r["score"]} for r in results]
    ))
    await db.flush()
    return results


async def retrieve_platform_knowledge(
    db: AsyncSession, query: str, top_k: int = 5,
    vector_service: VectorService | None = None, caller: str = "service"
) -> list[dict]:
    service = vector_service or get_vector_service()
    results = await service.query(query, {"scope": "platform"}, max(1, min(top_k, 20)))
    db.add(RagRetrievalLog(
        user_id=None, query_text=query[:500], caller=caller,
        results=[{"document_id": r["metadata"].get("document_id"), "score": r["score"]} for r in results]
    ))
    await db.flush()
    return results
