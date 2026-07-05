from httpx import AsyncClient
import pytest
from sqlalchemy import select

from core.auth import hash_password
from core.agent_workflow import run_qa_agent_workflow
from models.audit import AdminActionLog, AuditLog
from models.product import ProductCategory, ProductStatus
from models.user import User
from tests.test_auth_user_address import auth_headers, login_user, register_user


pytestmark = pytest.mark.asyncio


async def create_admin(session_factory, password: str) -> User:
    async with session_factory() as session:
        admin = User(
            phone="13800138999",
            nickname="admin",
            password_hash=hash_password(password),
            is_admin=True,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        return admin


async def test_adoption_apply_duplicate_and_admin_audit(test_context, strong_password):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]
    session_factory = test_context["session_factory"]

    await register_user(client, cache, "13800138101", strong_password)
    publisher_token = await login_user(client, "13800138101", strong_password)
    await register_user(client, cache, "13800138102", strong_password)
    applicant_token = await login_user(client, "13800138102", strong_password)
    await create_admin(session_factory, strong_password)
    admin_token = await login_user(client, "13800138999", strong_password)

    created = await client.post(
        "/adoptions",
        headers=auth_headers(publisher_token),
        json={
            "name": "Lucky",
            "species": "cat",
            "city": "Shanghai",
            "description": "Friendly cat",
        },
    )
    assert created.status_code == 200, created.text
    adoption_id = created.json()["id"]

    public_list = await client.get("/adoptions")
    assert public_list.status_code == 200
    assert len(public_list.json()) == 1

    application = await client.post(
        f"/adoptions/{adoption_id}/applications",
        headers=auth_headers(applicant_token),
        json={
            "contact_name": "Sang",
            "contact_phone": "13800138102",
            "living_city": "Shanghai",
            "living_condition": "apartment",
            "reason": "I can take good care of it",
        },
    )
    assert application.status_code == 200, application.text
    application_id = application.json()["id"]

    duplicate = await client.post(
        f"/adoptions/{adoption_id}/applications",
        headers=auth_headers(applicant_token),
        json={
            "contact_name": "Sang",
            "contact_phone": "13800138102",
            "living_city": "Shanghai",
            "living_condition": "apartment",
            "reason": "again",
        },
    )
    assert duplicate.status_code == 409

    forbidden = await client.post(
        f"/admin/adoptions/applications/{application_id}/approve",
        headers=auth_headers(applicant_token),
        json={"reason": "ok"},
    )
    assert forbidden.status_code == 403

    approved = await client.post(
        f"/admin/adoptions/applications/{application_id}/approve",
        headers=auth_headers(admin_token),
        json={"reason": "qualified"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["audited_by"] is not None

    async with session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(
                AuditLog.target_type == "adoption_application",
                AuditLog.target_id == application_id,
            )
        )
        assert result.scalar_one_or_none() is not None


async def test_merchant_apply_and_admin_approve_sets_user_merchant(test_context, strong_password):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]
    session_factory = test_context["session_factory"]

    await register_user(client, cache, "13800138103", strong_password)
    merchant_token = await login_user(client, "13800138103", strong_password)
    await create_admin(session_factory, strong_password)
    admin_token = await login_user(client, "13800138999", strong_password)

    applied = await client.post(
        "/merchants/apply",
        headers=auth_headers(merchant_token),
        json={
            "shop_name": "Sang Pet Shop",
            "contact_name": "Sang",
            "contact_phone": "13800138103",
            "business_scope": "pet food",
            "qualifications": [
                {
                    "qualification_type": "business_license",
                    "file_name": "license.pdf",
                    "file_url": "/generated/license.pdf",
                }
            ],
        },
    )
    assert applied.status_code == 200, applied.text
    merchant_id = applied.json()["id"]
    assert applied.json()["status"] == "pending"
    assert len(applied.json()["qualifications"]) == 1

    pending = await client.get("/admin/merchants/pending", headers=auth_headers(admin_token))
    assert pending.status_code == 200
    assert len(pending.json()) == 1

    approved = await client.post(
        f"/admin/merchants/{merchant_id}/approve",
        headers=auth_headers(admin_token),
        json={"reason": "materials ok"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    me = await client.get("/users/me", headers=auth_headers(merchant_token))
    assert me.status_code == 200
    assert me.json()["is_merchant"] is True

    products = await client.get("/merchants/me/products", headers=auth_headers(merchant_token))
    assert products.status_code == 200
    assert products.json() == []

    async with session_factory() as session:
        category = ProductCategory(name="Merchant Food", sort_order=1)
        session.add(category)
        await session.commit()
        await session.refresh(category)
        category_id = category.id

    created_product = await client.post(
        "/merchants/me/products",
        headers=auth_headers(merchant_token),
        json={
            "category_id": category_id,
            "title": "Sang Cat Food",
            "description": "merchant product",
            "applicable_pet_type": "cat",
            "skus": [
                {
                    "sku_code": "SANG-CAT-FOOD-1",
                    "name": "1kg",
                    "specs": {"weight": "1kg"},
                    "price": 1000,
                    "original_price": 1200,
                    "stock": 10,
                }
            ],
            "images": [{"image_url": "/generated/product/sang-cat-food.png"}],
        },
    )
    assert created_product.status_code == 200, created_product.text
    product = created_product.json()["product"]
    product_id = product["id"]
    sku_id = product["skus"][0]["id"]
    assert product["status"] == ProductStatus.DRAFT.value

    submitted = await client.post(
        f"/merchants/me/products/{product_id}/submit",
        headers=auth_headers(merchant_token),
        json={"reason": "ready"},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == ProductStatus.PENDING.value

    pending_products = await client.get("/admin/products/pending", headers=auth_headers(admin_token))
    assert pending_products.status_code == 200
    assert pending_products.json()["total"] == 1

    approved_product = await client.post(
        f"/admin/products/{product_id}/approve",
        headers=auth_headers(admin_token),
        json={"reason": "ok"},
    )
    assert approved_product.status_code == 200, approved_product.text

    off_sale = await client.post(
        f"/merchants/me/products/{product_id}/off-sale",
        headers=auth_headers(merchant_token),
        json={"reason": "pause"},
    )
    assert off_sale.status_code == 200, off_sale.text
    assert off_sale.json()["status"] == ProductStatus.OFF_SHELF.value

    discount = await client.post(
        f"/merchants/me/products/{product_id}/discount",
        headers=auth_headers(merchant_token),
        json={"sku_prices": {str(sku_id): 900}, "reason": "promotion"},
    )
    assert discount.status_code == 200, discount.text


async def test_admin_freeze_user_invalidates_token_and_logs_action(test_context, strong_password):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]
    session_factory = test_context["session_factory"]

    registered = await register_user(client, cache, "13800138104", strong_password)
    user_token = await login_user(client, "13800138104", strong_password)
    await create_admin(session_factory, strong_password)
    admin_token = await login_user(client, "13800138999", strong_password)

    frozen = await client.post(
        f"/admin/users/{registered['id']}/freeze",
        headers=auth_headers(admin_token),
        json={"reason": "risk"},
    )
    assert frozen.status_code == 200, frozen.text
    assert frozen.json()["is_frozen"] is True

    old_token_result = await client.get("/users/me", headers=auth_headers(user_token))
    assert old_token_result.status_code == 401

    async with session_factory() as session:
        result = await session.execute(
            select(AdminActionLog).where(
                AdminActionLog.target_type == "user",
                AdminActionLog.target_id == registered["id"],
            )
        )
        assert result.scalar_one_or_none() is not None


async def test_qa_agent_medical_and_high_risk_safety_prompt(test_context, strong_password):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]

    await register_user(client, cache, "13800138105", strong_password)
    token = await login_user(client, "13800138105", strong_password)

    session = await client.post(
        "/agents/qa/sessions",
        headers=auth_headers(token),
        json={"title": "cat care"},
    )
    assert session.status_code == 200, session.text
    session_id = session.json()["id"]

    medical = await client.post(
        f"/agents/qa/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "猫咪拉稀可以怎么用药，剂量是多少？"},
    )
    assert medical.status_code == 200, medical.text
    answer = medical.json()["assistant_message"]
    assert answer["risk_level"] == "medical"
    assert "不能替代兽医诊断" in answer["content"]

    high = await client.post(
        f"/agents/qa/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "狗狗中毒抽搐怎么办？"},
    )
    assert high.status_code == 200, high.text
    high_answer = high.json()["assistant_message"]
    assert high_answer["risk_level"] == "high"
    assert "宠物医院" in high_answer["content"]

    detail = await client.get(f"/agents/sessions/{session_id}", headers=auth_headers(token))
    assert detail.status_code == 200
    assert len(detail.json()["messages"]) == 4


async def test_qa_agent_workflow_accepts_session_id_without_memory_dsn():
    result = await run_qa_agent_workflow(
        question="猫咪换粮要注意什么？",
        risk_level="normal",
        history=[],
        session_id=123,
    )
    assert result["answer"]
    assert result["risk_level"] == "normal"
