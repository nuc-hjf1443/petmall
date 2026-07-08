from httpx import AsyncClient
import pytest
from sqlalchemy import select

from core.auth import hash_password
from core.agent_workflow import run_qa_agent_workflow
from models.audit import AdminActionLog, AuditLog
from models.merchant import Merchant
from models.order import Order, OrderItem, PaymentStatus, PaymentTransaction
from models.pet import PetDetailProfile, PetProfile
from models.product import Product, ProductCategory, ProductSku, ProductStatus
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


async def test_admin_platform_pets_orders_and_statistics(test_context, strong_password):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]
    session_factory = test_context["session_factory"]

    user = await register_user(client, cache, "13800138106", strong_password)
    user_token = await login_user(client, "13800138106", strong_password)
    await create_admin(session_factory, strong_password)
    admin_token = await login_user(client, "13800138999", strong_password)

    async with session_factory() as session:
        merchant = Merchant(
            owner_user_id=user["id"],
            shop_name="Admin View Shop",
            contact_name="Sang",
            contact_phone="13800138106",
            business_scope="pet food",
            status="approved",
        )
        pet = PetProfile(user_id=user["id"], name="Mimi", pet_type="cat", breed="British Shorthair")
        session.add_all([merchant, pet])
        await session.flush()
        session.add(PetDetailProfile(user_id=user["id"], pet_id=pet.id, profile_completeness=80))
        order = Order(
            order_no="PMADMIN001",
            user_id=user["id"],
            merchant_id=merchant.id,
            total_amount=1200,
            discount_amount=100,
            coin_deduct_amount=0,
            pay_amount=1100,
            status="paid",
            address_snapshot={
                "receiver_name": "Sang",
                "receiver_phone": "13800138106",
                "province": "Shanghai",
                "city": "Shanghai",
                "district": "Pudong",
                "detail_address": "No.1 Road",
            },
        )
        order.items.append(
            OrderItem(
                product_id=1,
                sku_id=1,
                product_title="Cat Food",
                sku_name="1kg",
                sku_specs={"weight": "1kg"},
                product_image=None,
                unit_price=1100,
                quantity=1,
                subtotal=1100,
            )
        )
        session.add(order)
        await session.flush()
        session.add(
            PaymentTransaction(
                out_trade_no="TRADEADMIN001",
                business_type="order",
                business_id=order.id,
                pay_channel="mock",
                payment_mode="mock",
                amount=1100,
                status=PaymentStatus.PAID.value,
            )
        )
        await session.commit()
        order_id = order.id

    forbidden = await client.get("/admin/pets", headers=auth_headers(user_token))
    assert forbidden.status_code == 403

    pets = await client.get("/admin/pets?keyword=Mimi", headers=auth_headers(admin_token))
    assert pets.status_code == 200, pets.text
    assert pets.json()["total"] == 1
    assert pets.json()["items"][0]["owner_phone"] == "13800138106"
    assert pets.json()["items"][0]["profile_completeness"] == 80

    orders = await client.get("/admin/orders?order_no=PMADMIN001", headers=auth_headers(admin_token))
    assert orders.status_code == 200, orders.text
    assert orders.json()["total"] == 1
    assert orders.json()["items"][0]["payment_status"] == PaymentStatus.PAID.value
    assert orders.json()["items"][0]["items"][0]["product_title"] == "Cat Food"

    order_detail = await client.get(f"/admin/orders/{order_id}", headers=auth_headers(admin_token))
    assert order_detail.status_code == 200, order_detail.text
    assert order_detail.json()["merchant_name"] == "Admin View Shop"

    overview = await client.get("/admin/statistics/overview", headers=auth_headers(admin_token))
    assert overview.status_code == 200, overview.text
    assert overview.json()["gmv"] == 1100
    assert overview.json()["paid_order_count"] == 1
    assert overview.json()["pet_count"] == 1

    trend = await client.get("/admin/statistics/orders-trend?days=7", headers=auth_headers(admin_token))
    assert trend.status_code == 200, trend.text
    assert sum(item["gmv"] for item in trend.json()["items"]) == 1100


async def test_admin_off_sale_product_and_force_cancel_order(test_context, strong_password):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]
    session_factory = test_context["session_factory"]

    user = await register_user(client, cache, "13800138107", strong_password)
    user_token = await login_user(client, "13800138107", strong_password)
    await create_admin(session_factory, strong_password)
    admin_token = await login_user(client, "13800138999", strong_password)

    async with session_factory() as session:
        merchant = Merchant(
            owner_user_id=user["id"],
            shop_name="Force Ops Shop",
            contact_name="Sang",
            contact_phone="13800138107",
            business_scope="pet food",
            status="approved",
        )
        category = ProductCategory(name="Force Ops Food", sort_order=1)
        session.add_all([merchant, category])
        await session.flush()
        product = Product(
            merchant_id=merchant.id,
            category_id=category.id,
            title="Force Cancel Cat Food",
            price=1000,
            stock=3,
            status=ProductStatus.ON_SALE.value,
            description="for admin force tests",
            applicable_pet_type="cat",
        )
        session.add(product)
        await session.flush()
        sku = ProductSku(
            product_id=product.id,
            sku_code="FORCE-CAT-FOOD-1",
            name="1kg",
            specs={"weight": "1kg"},
            price=1000,
            stock=3,
        )
        session.add(sku)
        await session.flush()
        order = Order(
            order_no="PMFORCE001",
            user_id=user["id"],
            merchant_id=merchant.id,
            total_amount=2000,
            discount_amount=0,
            coin_deduct_amount=0,
            pay_amount=2000,
            status="pending_payment",
            address_snapshot={
                "receiver_name": "Sang",
                "receiver_phone": "13800138107",
                "province": "Shanghai",
                "city": "Shanghai",
                "district": "Pudong",
                "detail_address": "No.2 Road",
            },
        )
        order.items.append(
            OrderItem(
                product_id=product.id,
                sku_id=sku.id,
                product_title=product.title,
                sku_name=sku.name,
                sku_specs=sku.specs,
                product_image=None,
                unit_price=1000,
                quantity=2,
                subtotal=2000,
            )
        )
        product.stock = 1
        sku.stock = 1
        session.add(order)
        await session.flush()
        session.add(
            PaymentTransaction(
                out_trade_no="TRADEFORCE001",
                business_type="order",
                business_id=order.id,
                pay_channel="mock",
                payment_mode="mock",
                amount=2000,
                status=PaymentStatus.CREATED.value,
            )
        )
        await session.commit()
        product_id = product.id
        order_id = order.id
        sku_id = sku.id

    user_off_sale = await client.post(
        f"/admin/products/{product_id}/off-sale",
        headers=auth_headers(user_token),
        json={"reason": "risk"},
    )
    assert user_off_sale.status_code == 403

    off_sale = await client.post(
        f"/admin/products/{product_id}/off-sale",
        headers=auth_headers(admin_token),
        json={"reason": "admin risk control"},
    )
    assert off_sale.status_code == 200, off_sale.text

    user_cancel = await client.post(
        f"/admin/orders/{order_id}/force-cancel",
        headers=auth_headers(user_token),
        json={"reason": "risk"},
    )
    assert user_cancel.status_code == 403

    cancelled = await client.post(
        f"/admin/orders/{order_id}/force-cancel",
        headers=auth_headers(admin_token),
        json={"reason": "customer risk"},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["payment_status"] == PaymentStatus.CLOSED.value

    cancelled_again = await client.post(
        f"/admin/orders/{order_id}/force-cancel",
        headers=auth_headers(admin_token),
        json={"reason": "retry"},
    )
    assert cancelled_again.status_code == 200, cancelled_again.text

    async with session_factory() as session:
        stored_product = await session.get(Product, product_id)
        stored_sku = await session.get(ProductSku, sku_id)
        assert stored_product.status == ProductStatus.OFF_SHELF.value
        assert stored_product.stock == 3
        assert stored_sku.stock == 3
        logs = (
            await session.execute(
                select(AdminActionLog).where(
                    AdminActionLog.target_type == "order",
                    AdminActionLog.target_id == order_id,
                    AdminActionLog.action == "force_cancel",
                )
            )
        ).scalars().all()
        assert len(logs) == 1


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

    sessions = await client.get("/agents/qa/sessions", headers=auth_headers(token))
    assert sessions.status_code == 200
    assert sessions.json()[0]["id"] == session_id
    assert sessions.json()[0]["message_count"] == 4
    assert sessions.json()[0]["last_role"] == "assistant"

    deleted = await client.delete(f"/agents/qa/sessions/{session_id}", headers=auth_headers(token))
    assert deleted.status_code == 200

    missing = await client.get(f"/agents/sessions/{session_id}", headers=auth_headers(token))
    assert missing.status_code == 404

    empty_sessions = await client.get("/agents/qa/sessions", headers=auth_headers(token))
    assert empty_sessions.status_code == 200
    assert empty_sessions.json() == []


async def test_qa_agent_workflow_accepts_session_id_without_memory_dsn():
    result = await run_qa_agent_workflow(
        question="猫咪换粮要注意什么？",
        risk_level="normal",
        history=[],
        session_id=123,
    )
    assert result["answer"]
    assert result["risk_level"] == "normal"


async def test_agent_memory_status_requires_auth_and_reports_dependency(test_context, strong_password):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]

    unauthorized = await client.get("/agents/memory/status")
    assert unauthorized.status_code == 401

    await register_user(client, cache, "13800138108", strong_password)
    token = await login_user(client, "13800138108", strong_password)

    response = await client.get("/agents/memory/status", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "postgres"
    assert body["dependency_available"] is True
    assert body["thread_id_pattern"] == "qa_session:{session_id}"
