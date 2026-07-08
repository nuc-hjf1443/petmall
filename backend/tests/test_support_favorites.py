import pytest
from sqlalchemy import select

from models.adoption import AdoptionApplication, AdoptionPet
from models.merchant import Merchant
from models.product import Product, ProductCategory, ProductSku
from models.user import User
from tests.test_order_payment import auth, register


pytestmark = pytest.mark.asyncio


async def _make_admin(session_factory, phone: str) -> None:
    async with session_factory() as db:
        user = (await db.execute(select(User).where(User.phone == phone))).scalar_one()
        user.is_admin = True
        await db.commit()


async def _seed_shop_product(session_factory, owner_phone: str) -> dict[str, int]:
    async with session_factory() as db:
        owner = (await db.execute(select(User).where(User.phone == owner_phone))).scalar_one()
        merchant = Merchant(
            owner_user_id=owner.id,
            shop_name="Support Shop",
            contact_name="Owner",
            contact_phone=owner_phone,
            business_scope="pet food",
            status="approved",
        )
        owner.is_merchant = True
        category = ProductCategory(name="Support Food", is_enabled=True)
        db.add_all([merchant, category])
        await db.flush()
        product = Product(
            merchant_id=merchant.id,
            category_id=category.id,
            title="Support Cat Food",
            price=1000,
            stock=5,
            status="on_sale",
        )
        db.add(product)
        await db.flush()
        db.add(ProductSku(
            product_id=product.id,
            sku_code="SUPPORT-CAT-1",
            name="1kg",
            specs={},
            price=1000,
            stock=5,
        ))
        await db.commit()
        return {"merchant_id": merchant.id, "product_id": product.id}


async def test_platform_and_merchant_support_flow(test_context, strong_password):
    client = test_context["client"]
    cache = test_context["cache"]
    session_factory = test_context["session_factory"]

    user_token = await register(client, cache, "13940000001", strong_password)
    merchant_token = await register(client, cache, "13940000002", strong_password)
    admin_token = await register(client, cache, "13940000003", strong_password)
    await _make_admin(session_factory, "13940000003")
    seeded = await _seed_shop_product(session_factory, "13940000002")

    platform = await client.post("/support/platform", headers=auth(user_token))
    assert platform.status_code == 200, platform.text
    platform_id = platform.json()["id"]
    sent = await client.post(
        f"/support/conversations/{platform_id}/messages",
        headers=auth(user_token),
        json={"content": "Need platform help"},
    )
    assert sent.status_code == 200, sent.text
    assert sent.json()["messages"][0]["content"] == "Need platform help"

    admin_list = await client.get("/admin/support/conversations", headers=auth(admin_token))
    assert admin_list.status_code == 200, admin_list.text
    assert admin_list.json()["total"] == 1
    admin_reply = await client.post(
        f"/admin/support/conversations/{platform_id}/messages",
        headers=auth(admin_token),
        json={"content": "Platform reply"},
    )
    assert admin_reply.status_code == 200, admin_reply.text
    resolved = await client.put(
        f"/admin/support/conversations/{platform_id}/status",
        headers=auth(admin_token),
        json={"status": "resolved"},
    )
    assert resolved.json()["status"] == "resolved"

    merchant_conversation = await client.post(
        f"/support/products/{seeded['product_id']}/merchant",
        headers=auth(user_token),
    )
    assert merchant_conversation.status_code == 200, merchant_conversation.text
    merchant_conversation_id = merchant_conversation.json()["id"]

    forbidden = await client.get(
        f"/support/conversations/{merchant_conversation_id}",
        headers=auth(admin_token),
    )
    assert forbidden.status_code == 200

    merchant_reply = await client.post(
        f"/merchants/me/support/conversations/{merchant_conversation_id}/messages",
        headers=auth(merchant_token),
        json={"content": "Merchant reply"},
    )
    assert merchant_reply.status_code == 200, merchant_reply.text
    merchant_list = await client.get("/merchants/me/support/conversations", headers=auth(merchant_token))
    assert merchant_list.status_code == 200
    assert merchant_list.json()["items"][0]["merchant_id"] == seeded["merchant_id"]

    transferred = await client.post(
        f"/merchants/me/support/conversations/{merchant_conversation_id}/transfer",
        headers=auth(merchant_token),
    )
    assert transferred.status_code == 200, transferred.text
    assert transferred.json()["assigned_to_platform"] is True

    admin_transferred = await client.get("/admin/support/conversations", headers=auth(admin_token))
    assert admin_transferred.json()["total"] == 2
    admin_merchant_reply = await client.post(
        f"/admin/support/conversations/{merchant_conversation_id}/messages",
        headers=auth(admin_token),
        json={"content": "Platform took over"},
    )
    assert admin_merchant_reply.status_code == 200, admin_merchant_reply.text


async def test_product_favorite_and_merchant_follow(test_context, strong_password):
    client = test_context["client"]
    cache = test_context["cache"]
    session_factory = test_context["session_factory"]

    user_token = await register(client, cache, "13940000011", strong_password)
    await register(client, cache, "13940000012", strong_password)
    seeded = await _seed_shop_product(session_factory, "13940000012")

    detail = await client.get(f"/products/{seeded['product_id']}", headers=auth(user_token))
    assert detail.status_code == 200, detail.text
    assert detail.json()["favorited_by_me"] is False
    assert detail.json()["following_merchant"] is False
    assert detail.json()["merchant"]["id"] == seeded["merchant_id"]

    assert (await client.post(f"/products/{seeded['product_id']}/favorite", headers=auth(user_token))).status_code == 200
    assert (await client.post(f"/products/{seeded['product_id']}/favorite", headers=auth(user_token))).status_code == 200
    assert (await client.post(f"/merchants/{seeded['merchant_id']}/follow", headers=auth(user_token))).status_code == 200
    assert (await client.post(f"/merchants/{seeded['merchant_id']}/follow", headers=auth(user_token))).status_code == 200

    detail = await client.get(f"/products/{seeded['product_id']}", headers=auth(user_token))
    assert detail.json()["favorited_by_me"] is True
    assert detail.json()["following_merchant"] is True

    favorites = await client.get("/products/favorites", headers=auth(user_token))
    assert favorites.status_code == 200, favorites.text
    assert favorites.json()["total"] == 1

    assert (await client.delete(f"/products/{seeded['product_id']}/favorite", headers=auth(user_token))).status_code == 200
    assert (await client.delete(f"/merchants/{seeded['merchant_id']}/follow", headers=auth(user_token))).status_code == 200
    detail = await client.get(f"/products/{seeded['product_id']}", headers=auth(user_token))
    assert detail.json()["favorited_by_me"] is False
    assert detail.json()["following_merchant"] is False


async def test_adoption_conversation_permissions(test_context, strong_password):
    client = test_context["client"]
    cache = test_context["cache"]
    session_factory = test_context["session_factory"]

    publisher_token = await register(client, cache, "13940000021", strong_password)
    applicant_token = await register(client, cache, "13940000022", strong_password)
    other_token = await register(client, cache, "13940000023", strong_password)

    async with session_factory() as db:
        publisher = (await db.execute(select(User).where(User.phone == "13940000021"))).scalar_one()
        applicant = (await db.execute(select(User).where(User.phone == "13940000022"))).scalar_one()
        adoption = AdoptionPet(
            publisher_id=publisher.id,
            name="Lucky",
            species="cat",
            city="Shanghai",
            description="Friendly",
        )
        db.add(adoption)
        await db.flush()
        application = AdoptionApplication(
            adoption_pet_id=adoption.id,
            applicant_id=applicant.id,
            contact_name="Applicant",
            contact_phone="13940000022",
            living_city="Shanghai",
            living_condition="apartment",
            reason="I like Lucky",
        )
        db.add(application)
        await db.commit()
        adoption_id = adoption.id
        application_id = application.id

    created = await client.post(
        f"/support/adoptions/{adoption_id}?application_id={application_id}",
        headers=auth(applicant_token),
    )
    assert created.status_code == 200, created.text
    conversation_id = created.json()["id"]
    sent = await client.post(
        f"/support/conversations/{conversation_id}/messages",
        headers=auth(applicant_token),
        json={"content": "Can we talk about Lucky?"},
    )
    assert sent.status_code == 200, sent.text

    publisher_detail = await client.get(
        f"/support/conversations/{conversation_id}",
        headers=auth(publisher_token),
    )
    assert publisher_detail.status_code == 200, publisher_detail.text
    assert publisher_detail.json()["messages"][0]["content"] == "Can we talk about Lucky?"

    published_list = await client.get("/support/adoptions/published", headers=auth(publisher_token))
    assert published_list.status_code == 200, published_list.text
    assert published_list.json()["total"] == 1

    denied = await client.get(f"/support/conversations/{conversation_id}", headers=auth(other_token))
    assert denied.status_code == 403
