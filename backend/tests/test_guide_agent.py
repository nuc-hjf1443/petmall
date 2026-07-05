from httpx import AsyncClient
import pytest
from sqlalchemy import select

from models.agent import AgentRecommendation
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
    assert "cannot replace a veterinarian diagnosis" in body["assistant_message"]["content"]
    assert body["recommendations"] == []
