from pathlib import Path

import pytest

from core.knowledge_queue import get_knowledge_task_publisher
from core.rag_service import retrieve_platform_knowledge, retrieve_private_knowledge
from models.knowledge import KnowledgeDocument, KnowledgeTask
from services.knowledge_service import (
    create_platform_knowledge_document,
    get_pet_profile_document_adapter,
    process_knowledge_task,
)
from services.profile_document_service import RealPetProfileDocumentAdapter
from settings.config import get_settings
from tests.test_order_payment import auth, register


pytestmark = pytest.mark.asyncio


class FakePublisher:
    def __init__(self):
        self.task_ids: list[int] = []

    async def publish(self, task_id: int) -> None:
        self.task_ids.append(task_id)


class FakeVectors:
    def __init__(self):
        self.values: dict[str, tuple[str, dict]] = {}
        self.last_where = None

    async def upsert(self, ids, texts, metadata):
        self.values.update({key: (text, meta) for key, text, meta in zip(ids, texts, metadata)})

    async def delete_document(self, document_id):
        self.values = {
            key: value for key, value in self.values.items()
            if value[1]["document_id"] != document_id
        }

    async def query(self, query, where, top_k):
        self.last_where = where
        filters = where.get("$and", [where])
        matches = [
            {"content": text, "metadata": meta, "score": 1.0}
            for text, meta in self.values.values()
            if all(
                all(meta.get(key) == value for key, value in item.items())
                for item in filters
            )
        ]
        return matches[:top_k]


async def test_pet_profile_document_uses_real_adapter_by_default():
    assert isinstance(
        get_pet_profile_document_adapter(),
        RealPetProfileDocumentAdapter,
    )


async def test_knowledge_isolation_index_and_delete(test_context, strong_password, tmp_path):
    client = test_context["client"]
    publisher = FakePublisher()
    client._transport.app.dependency_overrides[get_knowledge_task_publisher] = lambda: publisher
    settings = get_settings()
    original = settings.generated_asset_dir
    settings.generated_asset_dir = str(tmp_path)
    try:
        token_a = await register(client, test_context["cache"], "13940000001", strong_password)
        token_b = await register(client, test_context["cache"], "13940000002", strong_password)
        kb = await client.post("/knowledge-bases", headers=auth(token_a), json={"name": "private"})
        kb_id = kb.json()["id"]
        assert (await client.get(f"/knowledge-bases/{kb_id}", headers=auth(token_b))).status_code == 404
        uploaded = await client.post(
            f"/knowledge-bases/{kb_id}/documents", headers=auth(token_a),
            files={"file": ("safe.txt", "cat nutrition " * 100, "text/plain")},
        )
        assert uploaded.status_code == 200, uploaded.text
        document_id = uploaded.json()["id"]
        assert publisher.task_ids
        async with test_context["session_factory"]() as db:
            stored_document = await db.get(KnowledgeDocument, document_id)
            assert Path(stored_document.file_path).exists()
            private_url = (
                f"/generated/private/knowledge/1/{Path(stored_document.file_path).name}"
            )
        assert (await client.get(private_url)).status_code == 404

        vectors = FakeVectors()
        async with test_context["session_factory"]() as db:
            await process_knowledge_task(db, publisher.task_ids[-1], vectors)
            await process_knowledge_task(db, publisher.task_ids[-1], vectors)
            results = await retrieve_private_knowledge(db, 1, "nutrition", vector_service=vectors)
            assert results
            assert vectors.last_where == {"$and": [{"user_id": 1}, {"scope": "private"}]}
            other = await retrieve_private_knowledge(db, 2, "nutrition", vector_service=vectors)
            assert other == []
            await db.commit()
            platform = await create_platform_knowledge_document(
                db,
                title="Platform feeding guide",
                content="Provide clean drinking water every day.",
                publisher=publisher,
            )
            await process_knowledge_task(db, publisher.task_ids[-1], vectors)
            platform_results = await retrieve_platform_knowledge(
                db, "drinking water", vector_service=vectors
            )
            assert platform_results[0]["metadata"]["document_id"] == platform.id
            await db.commit()

        deleted = await client.delete(
            f"/knowledge-bases/{kb_id}/documents/{document_id}", headers=auth(token_a)
        )
        assert deleted.status_code == 200
        async with test_context["session_factory"]() as db:
            await process_knowledge_task(db, publisher.task_ids[-1], vectors)
            assert all(
                metadata["document_id"] != document_id
                for _, metadata in vectors.values.values()
            )
        assert not list((settings.private_asset_path / "knowledge" / "1").glob("*.txt"))
    finally:
        settings.generated_asset_dir = original
