import json
import logging

from httpx import AsyncClient
import pytest
from sqlalchemy import select

from models.agent import AgentRecommendation, AgentSession
from models.product import Product, ProductCategory, ProductSku, ProductStatus
from tests.test_auth_user_address import auth_headers, login_user, register_user


pytestmark = pytest.mark.asyncio


async def seed_catalog(session_factory) -> dict[str, int]:
    async with session_factory() as session:
        category = ProductCategory(name="Guide Cat Food", sort_order=10)
        session.add(category)
        await session.flush()

        product = Product(
            merchant_id=3001,
            category_id=category.id,
            title="Premium Cat Food",
            cover_image="/cat-food.png",
            price=1299,
            original_price=1599,
            stock=8,
            status=ProductStatus.ON_SALE.value,
            description="Chicken recipe for cats with sensitive stomachs",
            applicable_pet_type="cat",
        )
        hidden = Product(
            merchant_id=3001,
            category_id=category.id,
            title="Draft Cat Food",
            price=999,
            stock=8,
            status=ProductStatus.DRAFT.value,
            description="Hidden product",
            applicable_pet_type="cat",
        )
        session.add_all([product, hidden])
        await session.flush()

        sku = ProductSku(
            product_id=product.id,
            sku_code="GUIDE-CAT-FOOD-1KG",
            name="1 kg",
            specs={"weight": "1kg"},
            price=1299,
            original_price=1599,
            stock=8,
        )
        hidden_sku = ProductSku(
            product_id=hidden.id,
            sku_code="GUIDE-HIDDEN-CAT-FOOD",
            name="hidden",
            specs={},
            price=999,
            stock=8,
        )
        session.add_all([sku, hidden_sku])
        await session.flush()
        result = {"product_id": product.id, "sku_id": sku.id}
        await session.commit()
        return result


async def seed_dog_freeze_dried_catalog(session_factory) -> dict[str, int]:
    async with session_factory() as session:
        category = ProductCategory(name="Guide Dog Treat", sort_order=11)
        session.add(category)
        await session.flush()

        product = Product(
            merchant_id=3002,
            category_id=category.id,
            title="Dog Freeze Dried Treat",
            cover_image="/dog-freeze-dried.png",
            price=6999,
            original_price=7999,
            stock=5,
            status=ProductStatus.ON_SALE.value,
            description="\u72d7\u72d7\u51bb\u5e72\u96f6\u98df",
            applicable_pet_type="dog",
        )
        session.add(product)
        await session.flush()

        sku = ProductSku(
            product_id=product.id,
            sku_code="GUIDE-DOG-FREEZE-DRIED",
            name="500 g",
            specs={"weight": "500g"},
            price=6999,
            original_price=7999,
            stock=5,
        )
        session.add(sku)
        await session.flush()
        result = {"product_id": product.id, "sku_id": sku.id}
        await session.commit()
        return result


async def create_pet(client: AsyncClient, token: str) -> int:
    created = await client.post(
        "/pets",
        headers=auth_headers(token),
        json={
            "name": "Mimi",
            "pet_type": "cat",
            "breed": "Ragdoll",
            "weight": 3.8,
        },
    )
    assert created.status_code == 200, created.text
    return created.json()["id"]


async def create_dog_pet(client: AsyncClient, token: str) -> int:
    created = await client.post(
        "/pets",
        headers=auth_headers(token),
        json={
            "name": "\u53ef\u4e50",
            "pet_type": "dog",
            "breed": "Border Collie",
            "weight": 12.5,
        },
    )
    assert created.status_code == 200, created.text
    return created.json()["id"]


async def test_guide_agent_recommends_real_products_and_persists_result(
    test_context,
    strong_password,
    monkeypatch,
):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]
    session_factory = test_context["session_factory"]
    ids = await seed_catalog(session_factory)

    async def fake_retrieve_private_knowledge(*args, **kwargs):
        return [
            {
                "content": "Mimi prefers chicken cat food and needs slow food transition.",
                "metadata": {"document_id": 77},
                "score": 0.91,
            }
        ]

    monkeypatch.setattr(
        "services.guide_agent_service.retrieve_private_knowledge",
        fake_retrieve_private_knowledge,
    )

    await register_user(client, cache, "13960000001", strong_password)
    token = await login_user(client, "13960000001", strong_password)
    pet_id = await create_pet(client, token)

    created_session = await client.post(
        "/agents/guide/sessions",
        headers=auth_headers(token),
        json={"title": "cat food guide", "pet_id": pet_id},
    )
    assert created_session.status_code == 200, created_session.text
    session_id = created_session.json()["id"]
    assert created_session.json()["agent_type"] == "guide"

    response = await client.post(
        f"/agents/guide/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "Cat Food", "limit": 3},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["assistant_message"]["risk_level"] == "normal"
    assert body["assistant_message"]["references"] is not None
    assistant_content = body["assistant_message"]["content"]
    assert "product_id" not in assistant_content
    assert "sku_id" not in assistant_content
    assert "price=" not in assistant_content
    assert "stock=" not in assistant_content
    assert len(body["recommendations"]) == 1
    recommendation = body["recommendations"][0]
    assert recommendation["product_id"] == ids["product_id"]
    assert recommendation["sku_id"] == ids["sku_id"]
    assert recommendation["product"]["title"] == "Premium Cat Food"

    async with session_factory() as session:
        result = await session.execute(select(AgentRecommendation))
        stored = result.scalar_one()
        assert stored.product_id == ids["product_id"]
        assert stored.message_id == body["assistant_message"]["id"]
        assert stored.source in {"product_search", "rag_enhanced"}
        assert stored.source_detail
        assert stored.score is not None
        assert stored.matched_pet_fields is not None

    assert recommendation["source"] in {"product_search", "rag_enhanced"}
    assert recommendation["source_detail"]
    assert recommendation["score"] is not None
    assert isinstance(recommendation["matched_pet_fields"], list)


async def test_guide_agent_filters_fabricated_llm_product_ids(
    test_context,
    strong_password,
    monkeypatch,
):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]
    session_factory = test_context["session_factory"]
    await seed_catalog(session_factory)

    async def empty_retrieve_private_knowledge(*args, **kwargs):
        return []

    async def fabricated_workflow(**kwargs):
        return {
            "answer": "我推荐一个并不存在的商品。",
            "recommendations": [
                {
                    "product_id": 999999,
                    "sku_id": None,
                    "rank": 1,
                    "reason": "fabricated",
                    "source": "llm",
                    "source_detail": "llm_selected",
                    "score": 0.99,
                    "matched_pet_fields": ["pet_type"],
                },
                {
                    "product_id": "not-a-product-id",
                    "sku_id": "not-a-sku-id",
                    "rank": 2,
                    "reason": "malformed",
                    "source": "llm",
                },
            ],
            "references": None,
        }

    monkeypatch.setattr(
        "services.guide_agent_service.retrieve_private_knowledge",
        empty_retrieve_private_knowledge,
    )
    monkeypatch.setattr("services.guide_agent_service.run_guide_agent_workflow", fabricated_workflow)

    await register_user(client, cache, "13960000008", strong_password)
    token = await login_user(client, "13960000008", strong_password)

    created_session = await client.post(
        "/agents/guide/sessions",
        headers=auth_headers(token),
        json={"title": "fabrication guard"},
    )
    assert created_session.status_code == 200, created_session.text
    session_id = created_session.json()["id"]

    response = await client.post(
        f"/agents/guide/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "Cat Food", "limit": 3},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recommendations"] == []
    assistant_content = body["assistant_message"]["content"]
    assert "product_id" not in assistant_content
    assert "sku_id" not in assistant_content
    assert "完全匹配" in assistant_content or "补充" in assistant_content

    async with session_factory() as session:
        result = await session.execute(select(AgentRecommendation))
        assert result.scalars().all() == []


async def test_guide_agent_deduplicates_repeated_llm_product_ids(
    test_context,
    strong_password,
    monkeypatch,
):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]
    session_factory = test_context["session_factory"]
    ids = await seed_catalog(session_factory)

    async def empty_retrieve_private_knowledge(*args, **kwargs):
        return []

    async def repeated_workflow(**kwargs):
        return {
            "answer": f"推荐 product_id={ids['product_id']}, sku_id={ids['sku_id']}, price=1299, stock=8。",
            "recommendations": [
                {"product_id": ids["product_id"], "rank": 1, "reason": "first", "source": "llm"},
                {"product_id": ids["product_id"], "rank": 2, "reason": "duplicate", "source": "llm"},
            ],
            "references": None,
        }

    monkeypatch.setattr(
        "services.guide_agent_service.retrieve_private_knowledge",
        empty_retrieve_private_knowledge,
    )
    monkeypatch.setattr("services.guide_agent_service.run_guide_agent_workflow", repeated_workflow)

    await register_user(client, cache, "13960000009", strong_password)
    token = await login_user(client, "13960000009", strong_password)

    created_session = await client.post(
        "/agents/guide/sessions",
        headers=auth_headers(token),
        json={"title": "dedupe guard"},
    )
    assert created_session.status_code == 200, created_session.text
    session_id = created_session.json()["id"]

    response = await client.post(
        f"/agents/guide/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "Cat Food", "limit": 3},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["recommendations"]) == 1
    assert body["recommendations"][0]["product_id"] == ids["product_id"]
    assistant_content = body["assistant_message"]["content"]
    assert "product_id" not in assistant_content
    assert "sku_id" not in assistant_content
    assert "price=" not in assistant_content
    assert "stock=" not in assistant_content
    assert "商品卡片" in assistant_content

    async with session_factory() as session:
        result = await session.execute(select(AgentRecommendation))
        stored = result.scalars().all()
        assert len(stored) == 1
        assert stored[0].reason == "first"


async def test_guide_agent_logs_product_search_failure(
    test_context,
    strong_password,
    monkeypatch,
    caplog,
):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]

    async def failing_search(*args, **kwargs):
        raise RuntimeError("search unavailable")

    async def empty_retrieve_private_knowledge(*args, **kwargs):
        return []

    monkeypatch.setattr("services.guide_agent_service.search_products_for_agent", failing_search)
    monkeypatch.setattr(
        "services.guide_agent_service.retrieve_private_knowledge",
        empty_retrieve_private_knowledge,
    )

    await register_user(client, cache, "13960000010", strong_password)
    token = await login_user(client, "13960000010", strong_password)

    created_session = await client.post(
        "/agents/guide/sessions",
        headers=auth_headers(token),
        json={"title": "search failure"},
    )
    assert created_session.status_code == 200, created_session.text
    session_id = created_session.json()["id"]

    with caplog.at_level(logging.ERROR, logger="services.guide_agent_service"):
        response = await client.post(
            f"/agents/guide/sessions/{session_id}/messages",
            headers=auth_headers(token),
            json={"content": "Cat Food", "limit": 3},
        )

    assert response.status_code == 200, response.text
    assert response.json()["recommendations"] == []
    assert "guide_agent_product_search_failed" in caplog.text


async def test_guide_agent_logs_rag_failure(
    test_context,
    strong_password,
    monkeypatch,
    caplog,
):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]
    session_factory = test_context["session_factory"]
    await seed_catalog(session_factory)

    async def failing_retrieve_private_knowledge(*args, **kwargs):
        raise RuntimeError("rag unavailable")

    monkeypatch.setattr(
        "services.guide_agent_service.retrieve_private_knowledge",
        failing_retrieve_private_knowledge,
    )

    await register_user(client, cache, "13960000011", strong_password)
    token = await login_user(client, "13960000011", strong_password)

    created_session = await client.post(
        "/agents/guide/sessions",
        headers=auth_headers(token),
        json={"title": "rag failure"},
    )
    assert created_session.status_code == 200, created_session.text
    session_id = created_session.json()["id"]

    with caplog.at_level(logging.ERROR, logger="services.guide_agent_service"):
        response = await client.post(
            f"/agents/guide/sessions/{session_id}/messages",
            headers=auth_headers(token),
            json={"content": "Cat Food", "limit": 3},
        )

    assert response.status_code == 200, response.text
    assert "guide_agent_rag_failed" in caplog.text


async def test_guide_agent_logs_llm_failure(
    test_context,
    strong_password,
    monkeypatch,
    caplog,
):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]
    session_factory = test_context["session_factory"]
    ids = await seed_catalog(session_factory)

    async def empty_retrieve_private_knowledge(*args, **kwargs):
        return []

    async def failing_llm(*args, **kwargs):
        raise RuntimeError("llm unavailable")

    monkeypatch.setattr(
        "services.guide_agent_service.retrieve_private_knowledge",
        empty_retrieve_private_knowledge,
    )
    monkeypatch.setattr("core.agent_workflow._call_deepseek_guide", failing_llm)

    await register_user(client, cache, "13960000012", strong_password)
    token = await login_user(client, "13960000012", strong_password)

    created_session = await client.post(
        "/agents/guide/sessions",
        headers=auth_headers(token),
        json={"title": "llm failure"},
    )
    assert created_session.status_code == 200, created_session.text
    session_id = created_session.json()["id"]

    with caplog.at_level(logging.ERROR, logger="core.agent_workflow"):
        response = await client.post(
            f"/agents/guide/sessions/{session_id}/messages",
            headers=auth_headers(token),
            json={"content": "Cat Food", "limit": 3},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["recommendations"]) == 1
    assert body["recommendations"][0]["product_id"] == ids["product_id"]
    assert "guide_agent_llm_failed" in caplog.text


async def test_guide_agent_truncates_history_and_persists_summary(
    test_context,
    strong_password,
    monkeypatch,
):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]
    session_factory = test_context["session_factory"]
    captured: dict[str, object] = {}

    async def empty_retrieve_private_knowledge(*args, **kwargs):
        return []

    async def empty_search(*args, **kwargs):
        return []

    async def fake_summary(*, existing_summary, history, max_chars):
        captured["summary_input_size"] = len(history)
        return "summary text"

    async def fake_workflow(**kwargs):
        captured["history"] = kwargs["history"]
        captured["history_summary"] = kwargs["history_summary"]
        return {"answer": "ok", "recommendations": [], "references": None}

    monkeypatch.setattr("services.guide_agent_service.GUIDE_RECENT_HISTORY_LIMIT", 2)
    monkeypatch.setattr("services.guide_agent_service.search_products_for_agent", empty_search)
    monkeypatch.setattr(
        "services.guide_agent_service.retrieve_private_knowledge",
        empty_retrieve_private_knowledge,
    )
    monkeypatch.setattr("services.guide_agent_service.summarize_guide_history", fake_summary)
    monkeypatch.setattr("services.guide_agent_service.run_guide_agent_workflow", fake_workflow)

    await register_user(client, cache, "13960000013", strong_password)
    token = await login_user(client, "13960000013", strong_password)

    created_session = await client.post(
        "/agents/guide/sessions",
        headers=auth_headers(token),
        json={"title": "long history"},
    )
    assert created_session.status_code == 200, created_session.text
    session_id = created_session.json()["id"]

    for index in range(3):
        response = await client.post(
            f"/agents/guide/sessions/{session_id}/messages",
            headers=auth_headers(token),
            json={"content": f"message {index}", "limit": 3},
        )
        assert response.status_code == 200, response.text

    assert captured["history_summary"] == "summary text"
    assert captured["summary_input_size"] == 2
    assert len(captured["history"]) == 2

    async with session_factory() as session:
        stored_session = await session.get(AgentSession, session_id)
        assert stored_session is not None
        assert json.loads(stored_session.context_summary)["history_summary"] == "summary text"


async def test_guide_agent_lists_history_and_restores_latest_recommendations(
    test_context,
    strong_password,
    monkeypatch,
):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]
    session_factory = test_context["session_factory"]
    ids = await seed_catalog(session_factory)

    async def empty_retrieve_private_knowledge(*args, **kwargs):
        return []

    monkeypatch.setattr(
        "services.guide_agent_service.retrieve_private_knowledge",
        empty_retrieve_private_knowledge,
    )

    await register_user(client, cache, "13960000006", strong_password)
    token = await login_user(client, "13960000006", strong_password)
    await register_user(client, cache, "13960000007", strong_password)
    other_token = await login_user(client, "13960000007", strong_password)

    created_session = await client.post(
        "/agents/guide/sessions",
        headers=auth_headers(token),
        json={"title": "history guide"},
    )
    assert created_session.status_code == 200, created_session.text
    session_id = created_session.json()["id"]

    response = await client.post(
        f"/agents/guide/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "Cat Food", "limit": 3},
    )
    assert response.status_code == 200, response.text

    history = await client.get(
        "/agents/sessions",
        headers=auth_headers(token),
        params={"agent_type": "guide", "page": 1, "page_size": 10},
    )
    assert history.status_code == 200, history.text
    history_body = history.json()
    assert history_body["total"] == 1
    assert history_body["items"][0]["id"] == session_id
    assert history_body["items"][0]["title"] == "history guide"
    assert history_body["items"][0]["message_count"] == 2
    assert history_body["items"][0]["latest_message_content"]

    other_history = await client.get(
        "/agents/sessions",
        headers=auth_headers(other_token),
        params={"agent_type": "guide"},
    )
    assert other_history.status_code == 200, other_history.text
    assert other_history.json()["items"] == []

    recommendations = await client.get(
        f"/agents/guide/sessions/{session_id}/recommendations",
        headers=auth_headers(token),
    )
    assert recommendations.status_code == 200, recommendations.text
    recommendation_body = recommendations.json()
    assert len(recommendation_body) == 1
    assert recommendation_body[0]["product_id"] == ids["product_id"]
    assert recommendation_body[0]["product"]["title"] == "Premium Cat Food"

    cross_user_recommendations = await client.get(
        f"/agents/guide/sessions/{session_id}/recommendations",
        headers=auth_headers(other_token),
    )
    assert cross_user_recommendations.status_code == 404

    cross_user_delete = await client.delete(
        f"/agents/sessions/{session_id}",
        headers=auth_headers(other_token),
        params={"agent_type": "guide"},
    )
    assert cross_user_delete.status_code == 404

    deleted = await client.delete(
        f"/agents/sessions/{session_id}",
        headers=auth_headers(token),
        params={"agent_type": "guide"},
    )
    assert deleted.status_code == 200

    deleted_history = await client.get(
        "/agents/sessions",
        headers=auth_headers(token),
        params={"agent_type": "guide"},
    )
    assert deleted_history.status_code == 200
    assert deleted_history.json()["items"] == []


async def test_guide_agent_returns_no_recommendations_when_query_has_no_match(
    test_context,
    strong_password,
    monkeypatch,
):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]
    session_factory = test_context["session_factory"]
    await seed_catalog(session_factory)

    async def empty_retrieve_private_knowledge(*args, **kwargs):
        return []

    monkeypatch.setattr(
        "services.guide_agent_service.retrieve_private_knowledge",
        empty_retrieve_private_knowledge,
    )

    async def no_deepseek_guide(*args, **kwargs):
        return None

    monkeypatch.setattr("core.agent_workflow._call_deepseek_guide", no_deepseek_guide)

    await register_user(client, cache, "13960000005", strong_password)
    token = await login_user(client, "13960000005", strong_password)

    created_session = await client.post(
        "/agents/guide/sessions",
        headers=auth_headers(token),
        json={"title": "no match guide"},
    )
    assert created_session.status_code == 200, created_session.text
    session_id = created_session.json()["id"]

    response = await client.post(
        f"/agents/guide/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "帮我给宠物挑一套日常用品，预算三百", "limit": 3},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recommendations"] == []

    async with session_factory() as session:
        result = await session.execute(select(AgentRecommendation))
        assert result.scalars().all() == []


async def test_guide_agent_asks_questions_before_recommending_when_request_is_incomplete(
    test_context,
    strong_password,
):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]

    await register_user(client, cache, "13960000017", strong_password)
    token = await login_user(client, "13960000017", strong_password)

    created_session = await client.post(
        "/agents/guide/sessions",
        headers=auth_headers(token),
        json={"title": "clarify guide"},
    )
    assert created_session.status_code == 200, created_session.text
    session_id = created_session.json()["id"]

    response = await client.post(
        f"/agents/guide/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "\u60f3\u4e70\u70b9\u4e1c\u897f", "limit": 3},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["requires_user_confirmation"] is True
    assert body["recommendations"] == []
    assert body["next_questions"]
    assert body["guide_state"]["stage"] == "clarifying"


async def test_guide_agent_matches_pet_name_and_recommends_real_products(
    test_context,
    strong_password,
    monkeypatch,
):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]
    session_factory = test_context["session_factory"]
    ids = await seed_dog_freeze_dried_catalog(session_factory)

    async def empty_retrieve_private_knowledge(*args, **kwargs):
        return []

    monkeypatch.setattr(
        "services.guide_agent_service.retrieve_private_knowledge",
        empty_retrieve_private_knowledge,
    )

    await register_user(client, cache, "13960000018", strong_password)
    token = await login_user(client, "13960000018", strong_password)
    pet_id = await create_dog_pet(client, token)

    created_session = await client.post(
        "/agents/guide/sessions",
        headers=auth_headers(token),
        json={"title": "pet name guide"},
    )
    assert created_session.status_code == 200, created_session.text
    session_id = created_session.json()["id"]

    response = await client.post(
        f"/agents/guide/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "\u7ed9\u6211\u7684\u53ef\u4e50\u63a8\u8350\u51bb\u5e72\uff0c\u9884\u7b97 100 \u5143", "limit": 3},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["requires_user_confirmation"] is False
    assert len(body["recommendations"]) == 1
    assert body["recommendations"][0]["product_id"] == ids["product_id"]
    assert body["guide_state"]["slots"]["pet_id"] == pet_id
    assert body["guide_state"]["slots"]["pet_name"] == "\u53ef\u4e50"

    async with session_factory() as session:
        stored_session = await session.get(AgentSession, session_id)
        assert stored_session.pet_id == pet_id


async def test_guide_agent_does_not_recommend_cat_products_for_dog_request(
    test_context,
    strong_password,
    monkeypatch,
):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]
    session_factory = test_context["session_factory"]
    await seed_catalog(session_factory)

    async def empty_retrieve_private_knowledge(*args, **kwargs):
        return []

    async def no_deepseek_guide(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "services.guide_agent_service.retrieve_private_knowledge",
        empty_retrieve_private_knowledge,
    )
    monkeypatch.setattr("core.agent_workflow._call_deepseek_guide", no_deepseek_guide)

    await register_user(client, cache, "13960000016", strong_password)
    token = await login_user(client, "13960000016", strong_password)

    created_session = await client.post(
        "/agents/guide/sessions",
        headers=auth_headers(token),
        json={"title": "dog food guard"},
    )
    assert created_session.status_code == 200, created_session.text
    session_id = created_session.json()["id"]

    response = await client.post(
        f"/agents/guide/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "3 岁柯基，需要低敏狗粮，预算 300 元", "limit": 3},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recommendations"] == []

    async with session_factory() as session:
        result = await session.execute(select(AgentRecommendation))
        assert result.scalars().all() == []


async def test_guide_agent_rejects_cross_user_pet_and_session_access(test_context, strong_password):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]

    await register_user(client, cache, "13960000002", strong_password)
    token_a = await login_user(client, "13960000002", strong_password)
    await register_user(client, cache, "13960000003", strong_password)
    token_b = await login_user(client, "13960000003", strong_password)
    pet_id = await create_pet(client, token_a)

    forbidden_pet = await client.post(
        "/agents/guide/sessions",
        headers=auth_headers(token_b),
        json={"title": "bad", "pet_id": pet_id},
    )
    assert forbidden_pet.status_code == 404

    created_session = await client.post(
        "/agents/guide/sessions",
        headers=auth_headers(token_a),
        json={"title": "owner session", "pet_id": pet_id},
    )
    assert created_session.status_code == 200, created_session.text
    session_id = created_session.json()["id"]

    cross_user_read = await client.get(
        f"/agents/sessions/{session_id}",
        headers=auth_headers(token_b),
    )
    assert cross_user_read.status_code == 404


async def test_guide_agent_degrades_without_rag_or_products_and_flags_medical_risk(
    test_context,
    strong_password,
    monkeypatch,
):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]

    async def failing_retrieve_private_knowledge(*args, **kwargs):
        raise RuntimeError("rag unavailable")

    monkeypatch.setattr(
        "services.guide_agent_service.retrieve_private_knowledge",
        failing_retrieve_private_knowledge,
    )

    await register_user(client, cache, "13960000004", strong_password)
    token = await login_user(client, "13960000004", strong_password)

    created_session = await client.post(
        "/agents/guide/sessions",
        headers=auth_headers(token),
        json={"title": "medical guide"},
    )
    assert created_session.status_code == 200, created_session.text
    session_id = created_session.json()["id"]

    response = await client.post(
        f"/agents/guide/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "\u5904\u65b9\u7cae\u548c\u7528\u836f\u600e\u4e48\u9009", "limit": 3},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["assistant_message"]["risk_level"] == "medical"
    assert "不能替代兽医诊断" in body["assistant_message"]["content"]
    assert body["recommendations"] == []
