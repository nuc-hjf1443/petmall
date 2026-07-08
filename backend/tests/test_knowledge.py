from pathlib import Path

import pytest

from core.auth import create_access_token, hash_password
from core.knowledge_queue import get_knowledge_task_publisher
from core.rag_service import retrieve_platform_knowledge, retrieve_private_knowledge
from models.knowledge import KnowledgeDocument, KnowledgeTask
from models.user import User
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


async def test_admin_platform_knowledge_document_lifecycle(
    test_context, strong_password, tmp_path
):
    client = test_context["client"]
    publisher = FakePublisher()
    client._transport.app.dependency_overrides[get_knowledge_task_publisher] = lambda: publisher
    settings = get_settings()
    original = settings.generated_asset_dir
    settings.generated_asset_dir = str(tmp_path)
    try:
        async with test_context["session_factory"]() as db:
            admin = User(
                phone="13940000100",
                password_hash=hash_password(strong_password),
                is_admin=True,
            )
            normal = User(
                phone="13940000101",
                password_hash=hash_password(strong_password),
            )
            db.add_all([admin, normal])
            await db.commit()
            await db.refresh(admin)
            await db.refresh(normal)
            admin_token = create_access_token(admin.id, admin.token_version)
            normal_token = create_access_token(normal.id, normal.token_version)

        forbidden = await client.get(
            "/admin/knowledge/platform/documents",
            headers=auth(normal_token),
        )
        assert forbidden.status_code == 403

        kb = await client.get("/admin/knowledge/platform", headers=auth(admin_token))
        assert kb.status_code == 200, kb.text
        assert kb.json()["scope"] == "platform"

        uploaded = await client.post(
            "/admin/knowledge/platform/documents",
            headers=auth(admin_token),
            files={"file": ("platform.txt", "first platform feeding guide", "text/plain")},
        )
        assert uploaded.status_code == 200, uploaded.text
        document_id = uploaded.json()["id"]
        assert uploaded.json()["source_type"] == "platform_upload"
        assert publisher.task_ids

        vectors = FakeVectors()
        async with test_context["session_factory"]() as db:
            await process_knowledge_task(db, publisher.task_ids[-1], vectors)
            results = await retrieve_platform_knowledge(db, "feeding", vector_service=vectors)
            assert results
            assert results[0]["metadata"]["document_id"] == document_id
            assert results[0]["metadata"]["scope"] == "platform"
            await db.commit()

        listed = await client.get(
            "/admin/knowledge/platform/documents",
            headers=auth(admin_token),
        )
        assert listed.status_code == 200, listed.text
        assert [item["id"] for item in listed.json()] == [document_id]

        replaced = await client.put(
            f"/admin/knowledge/platform/documents/{document_id}",
            headers=auth(admin_token),
            files={"file": ("platform-v2.txt", "second platform hydration guide", "text/plain")},
        )
        assert replaced.status_code == 200, replaced.text
        assert replaced.json()["index_version"] == 2
        assert replaced.json()["file_name"] == "platform-v2.txt"

        async with test_context["session_factory"]() as db:
            await process_knowledge_task(db, publisher.task_ids[-1], vectors)
            results = await retrieve_platform_knowledge(db, "hydration", vector_service=vectors)
            assert results
            assert "second platform hydration guide" in results[0]["content"]
            assert all("first platform feeding guide" not in value[0] for value in vectors.values.values())
            await db.commit()

        private_token = await register(client, test_context["cache"], "13940000102", strong_password)
        private_kb = await client.post(
            "/knowledge-bases",
            headers=auth(private_token),
            json={"name": "private"},
        )
        private_upload = await client.post(
            f"/knowledge-bases/{private_kb.json()['id']}/documents",
            headers=auth(private_token),
            files={"file": ("private.txt", "private only", "text/plain")},
        )
        assert private_upload.status_code == 200, private_upload.text
        wrong_scope = await client.post(
            f"/admin/knowledge/platform/documents/{private_upload.json()['id']}/reindex",
            headers=auth(admin_token),
        )
        assert wrong_scope.status_code == 404

        deleted = await client.delete(
            f"/admin/knowledge/platform/documents/{document_id}",
            headers=auth(admin_token),
        )
        assert deleted.status_code == 200
        assert deleted.json()["message"] == "Platform document deletion scheduled"

        async with test_context["session_factory"]() as db:
            await process_knowledge_task(db, publisher.task_ids[-1], vectors)
            assert await retrieve_platform_knowledge(db, "hydration", vector_service=vectors) == []
            assert await db.get(KnowledgeDocument, document_id) is None
            await db.commit()
        assert not list((settings.private_asset_path / "knowledge" / "platform").glob("*.txt"))
    finally:
        settings.generated_asset_dir = original
