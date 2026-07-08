from httpx import AsyncClient
import pytest

from core.auth import hash_password
from core.errors import AppException
from main import app
from models.order import Order, OrderItem
from models.product import Product, ProductCategory, ProductSku, ProductStatus
from models.user import User
from schemas.product_schema import (
    ProductCreate,
    ProductImageInput,
    ProductSkuUpsert,
    ProductUpdate,
)
from services.product_service import (
    create_merchant_product,
    get_pending_products_for_audit,
    get_product_audit_detail,
    set_merchant_product_sale_status,
    submit_product_for_audit,
    update_merchant_product_discount,
    update_merchant_product,
    update_product_audit_status,
)
from services.review_service import ReviewPurchase, get_review_purchase_verifier


pytestmark = pytest.mark.asyncio


async def seed_catalog(session_factory) -> dict[str, int]:
    async with session_factory() as session:
        cat_food = ProductCategory(name="Pet Food", sort_order=10)
        cat_toys = ProductCategory(name="Pet Toys", sort_order=20)
        cat_hidden = ProductCategory(name="Hidden", sort_order=1, is_enabled=False)
        session.add_all([cat_food, cat_toys, cat_hidden])
        await session.flush()

        cat_food_id = cat_food.id
        cat_toys_id = cat_toys.id

        cat_product = Product(
            merchant_id=1001,
            category_id=cat_food.id,
            title="Premium Cat Food",
            cover_image="/cat-food.png",
            price=1299,
            original_price=1599,
            stock=5,
            status=ProductStatus.ON_SALE.value,
            brand="Royal",
            description="Chicken recipe for adult cats",
            applicable_pet_type="cat",
        )
        dog_product = Product(
            merchant_id=1001,
            category_id=cat_toys.id,
            title="Dog Ball",
            price=599,
            stock=10,
            status=ProductStatus.ON_SALE.value,
            brand="Pidan",
            applicable_pet_type="dog",
        )
        hidden_product = Product(
            merchant_id=1002,
            category_id=cat_food.id,
            title="Draft Cat Food",
            price=999,
            stock=20,
            status=ProductStatus.DRAFT.value,
            brand="Royal",
            applicable_pet_type="cat",
        )
        session.add_all([cat_product, dog_product, hidden_product])
        await session.flush()

        cat_sku = ProductSku(
            product_id=cat_product.id,
            sku_code="CAT-FOOD-1KG",
            name="1 kg",
            specs={"weight": "1kg"},
            price=1299,
            original_price=1599,
            stock=5,
        )
        disabled_sku = ProductSku(
            product_id=cat_product.id,
            sku_code="CAT-FOOD-2KG",
            name="2 kg",
            specs={"weight": "2kg"},
            price=2299,
            stock=0,
            is_enabled=False,
        )
        hidden_sku = ProductSku(
            product_id=hidden_product.id,
            sku_code="DRAFT-CAT-FOOD",
            name="Draft",
            specs={},
            price=999,
            stock=20,
        )
        session.add_all([cat_sku, disabled_sku, hidden_sku])
        await session.flush()

        result = {
            "cat_food_id": cat_food_id,
            "cat_toys_id": cat_toys_id,
            "cat_product_id": cat_product.id,
            "hidden_product_id": hidden_product.id,
            "cat_sku_id": cat_sku.id,
            "disabled_sku_id": disabled_sku.id,
            "hidden_sku_id": hidden_sku.id,
        }
        await session.commit()
        return result


async def seed_user(session_factory, phone: str, password: str) -> None:
    async with session_factory() as session:
        session.add(User(phone=phone, password_hash=hash_password(password)))
        await session.commit()


async def login(client: AsyncClient, phone: str, password: str) -> dict[str, str]:
    response = await client.post(
        "/auth/login",
        json={"account": phone, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_category_product_filter_and_detail_visibility(test_context):
    client: AsyncClient = test_context["client"]
    ids = await seed_catalog(test_context["session_factory"])

    categories = await client.get("/categories")
    assert categories.status_code == 200
    assert [item["name"] for item in categories.json()] == ["Pet Food", "Pet Toys"]

    products = await client.get(
        "/products",
        params={
            "keyword": "cat",
            "category_id": ids["cat_food_id"],
            "pet_type": "cat",
        },
    )
    assert products.status_code == 200
    body = products.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == ids["cat_product_id"]
    assert body["items"][0]["brand"] == "Royal"

    brand_products = await client.get("/products", params={"brand_keyword": "Pidan"})
    assert brand_products.status_code == 200
    assert brand_products.json()["total"] == 1
    assert brand_products.json()["items"][0]["title"] == "Dog Ball"

    price_asc = await client.get("/products", params={"sort": "price_asc"})
    assert price_asc.status_code == 200
    assert [item["title"] for item in price_asc.json()["items"]] == [
        "Dog Ball",
        "Premium Cat Food",
    ]

    detail = await client.get(f"/products/{ids['cat_product_id']}")
    assert detail.status_code == 200
    assert [sku["sku_code"] for sku in detail.json()["skus"]] == ["CAT-FOOD-1KG"]

    hidden = await client.get(f"/products/{ids['hidden_product_id']}")
    assert hidden.status_code == 404


async def test_product_sales_newest_and_price_sort(test_context):
    client: AsyncClient = test_context["client"]
    ids = await seed_catalog(test_context["session_factory"])

    async with test_context["session_factory"]() as session:
        order = Order(
            order_no="PMSORT001",
            user_id=1,
            merchant_id=1001,
            total_amount=1198,
            discount_amount=0,
            coin_deduct_amount=0,
            pay_amount=1198,
            status="paid",
            address_snapshot={
                "receiver_name": "Tester",
                "receiver_phone": "13800138000",
                "province": "Shanghai",
                "city": "Shanghai",
                "district": "Pudong",
                "detail_address": "No.1 Road",
            },
        )
        order.items.append(
            OrderItem(
                product_id=ids["cat_product_id"],
                sku_id=ids["cat_sku_id"],
                product_title="Premium Cat Food",
                sku_name="1 kg",
                sku_specs={"weight": "1kg"},
                product_image="/cat-food.png",
                unit_price=1299,
                quantity=2,
                subtotal=2598,
            )
        )
        session.add(order)
        await session.commit()

    sales = await client.get("/products", params={"sort": "sales"})
    assert sales.status_code == 200
    assert sales.json()["items"][0]["id"] == ids["cat_product_id"]

    price_desc = await client.get("/products", params={"sort": "price_desc"})
    assert price_desc.status_code == 200
    assert [item["title"] for item in price_desc.json()["items"]] == [
        "Premium Cat Food",
        "Dog Ball",
    ]

    newest = await client.get("/products", params={"sort": "newest"})
    assert newest.status_code == 200
    assert newest.json()["total"] == 2


async def test_cart_crud_stock_and_owner_isolation(test_context, strong_password):
    client: AsyncClient = test_context["client"]
    ids = await seed_catalog(test_context["session_factory"])
    await seed_user(test_context["session_factory"], "13800138101", strong_password)
    await seed_user(test_context["session_factory"], "13800138102", strong_password)
    headers_a = await login(client, "13800138101", strong_password)
    headers_b = await login(client, "13800138102", strong_password)

    unauthenticated = await client.get("/cart/items")
    assert unauthenticated.status_code == 401

    added = await client.post(
        "/cart/items",
        headers=headers_a,
        json={"sku_id": ids["cat_sku_id"], "quantity": 2},
    )
    assert added.status_code == 200, added.text
    item_id = added.json()["id"]
    assert added.json()["quantity"] == 2
    assert added.json()["subtotal"] == 2598

    repeated = await client.post(
        "/cart/items",
        headers=headers_a,
        json={"sku_id": ids["cat_sku_id"], "quantity": 1},
    )
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["id"] == item_id
    assert repeated.json()["quantity"] == 3

    overstock = await client.put(
        f"/cart/items/{item_id}",
        headers=headers_a,
        json={"quantity": 6},
    )
    assert overstock.status_code == 400

    disabled = await client.post(
        "/cart/items",
        headers=headers_a,
        json={"sku_id": ids["disabled_sku_id"], "quantity": 1},
    )
    assert disabled.status_code == 400

    off_shelf = await client.post(
        "/cart/items",
        headers=headers_a,
        json={"sku_id": ids["hidden_sku_id"], "quantity": 1},
    )
    assert off_shelf.status_code == 400

    owner_isolation = await client.put(
        f"/cart/items/{item_id}",
        headers=headers_b,
        json={"quantity": 1},
    )
    assert owner_isolation.status_code == 404

    updated = await client.put(
        f"/cart/items/{item_id}",
        headers=headers_a,
        json={"quantity": 4, "selected": False},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["quantity"] == 4
    assert updated.json()["selected"] is False

    listed = await client.get("/cart/items", headers=headers_a)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [item_id]

    deleted = await client.delete(f"/cart/items/{item_id}", headers=headers_a)
    assert deleted.status_code == 200
    empty = await client.get("/cart/items", headers=headers_a)
    assert empty.status_code == 200
    assert empty.json() == []


async def test_merchant_product_inventory_images_and_audit(test_context):
    session_factory = test_context["session_factory"]
    async with session_factory() as session:
        category = ProductCategory(name="Health", sort_order=1)
        session.add(category)
        await session.commit()
        await session.refresh(category)
        category_id = category.id

    async with session_factory() as session:
        created = await create_merchant_product(
            session,
            2001,
            ProductCreate(
                category_id=category_id,
                title="Pet Vitamins",
                brand="VetPlus",
                description="Daily supplement",
                applicable_pet_type="dog",
                skus=[
                    ProductSkuUpsert(
                        sku_code="VITAMIN-S",
                        name="Small",
                        specs={"size": "S"},
                        price=1200,
                        original_price=1500,
                        stock=5,
                    ),
                    ProductSkuUpsert(
                        sku_code="VITAMIN-L",
                        name="Large",
                        specs={"size": "L"},
                        price=1800,
                        stock=3,
                    ),
                ],
                images=[
                    ProductImageInput(image_url="/vitamin-1.png", sort_order=10),
                    ProductImageInput(image_url="/vitamin-2.png", sort_order=20),
                ],
            ),
        )
        product_id = created.id
        sku_small, sku_large = created.skus
        assert created.status == ProductStatus.DRAFT.value
        assert created.stock == 8
        assert created.price == 1200
        assert created.original_price == 1500
        assert created.cover_image == "/vitamin-1.png"
        assert created.images[0].is_primary is True

    async with session_factory() as session:
        with pytest.raises(AppException) as wrong_owner:
            await update_merchant_product(
                session,
                9999,
                product_id,
                ProductUpdate(title="Hijacked"),
            )
        assert wrong_owner.value.status_code == 404

    async with session_factory() as session:
        updated = await update_merchant_product(
            session,
            2001,
            product_id,
            ProductUpdate(
                skus=[
                    ProductSkuUpsert(
                        id=sku_small.id,
                        sku_code=sku_small.sku_code,
                        name=sku_small.name,
                        specs=sku_small.specs,
                        price=1100,
                        original_price=1400,
                        stock=7,
                    ),
                    ProductSkuUpsert(
                        id=sku_large.id,
                        sku_code=sku_large.sku_code,
                        name=sku_large.name,
                        specs=sku_large.specs,
                        price=1800,
                        stock=3,
                        is_enabled=False,
                    ),
                ],
                images=[
                    ProductImageInput(
                        image_url="/vitamin-new-1.png",
                        sort_order=20,
                    ),
                    ProductImageInput(
                        image_url="/vitamin-new-2.png",
                        sort_order=10,
                        is_primary=True,
                    ),
                ],
            ),
        )
        assert updated.stock == 7
        assert updated.price == 1100
        assert updated.original_price == 1400
        assert updated.cover_image == "/vitamin-new-2.png"
        assert [image.image_url for image in updated.images] == [
            "/vitamin-new-2.png",
            "/vitamin-new-1.png",
        ]

        pending = await submit_product_for_audit(session, 2001, product_id)
        assert pending.status == ProductStatus.PENDING.value
        assert pending.submitted_at is not None

        with pytest.raises(AppException) as pending_update:
            await update_merchant_product(
                session,
                2001,
                product_id,
                ProductUpdate(title="Not allowed"),
            )
        assert pending_update.value.status_code == 400

        with pytest.raises(AppException) as missing_reason:
            await update_product_audit_status(
                session,
                product_id,
                ProductStatus.REJECTED.value,
                None,
            )
        assert missing_reason.value.status_code == 400

        await update_product_audit_status(
            session,
            product_id,
            ProductStatus.REJECTED.value,
            "Label is unclear",
        )
        rejected = await get_product_audit_detail(session, product_id)
        assert rejected["status"] == ProductStatus.REJECTED.value
        assert rejected["audit_reason"] == "Label is unclear"
        assert len(rejected["skus"]) == 2

        await update_merchant_product(
            session,
            2001,
            product_id,
            ProductUpdate(title="Pet Vitamins Updated"),
        )
        await submit_product_for_audit(session, 2001, product_id)
        pending_page = await get_pending_products_for_audit(session)
        assert [item["id"] for item in pending_page["items"]] == [product_id]
        await update_product_audit_status(
            session,
            product_id,
            ProductStatus.ON_SALE.value,
            None,
        )
        approved = await get_product_audit_detail(session, product_id)
        assert approved["status"] == ProductStatus.ON_SALE.value
        assert approved["audit_reason"] is None
        first_sku_id = approved["skus"][0]["id"]
        discounted = await update_merchant_product_discount(
            session, 2001, product_id, {first_sku_id: 900}
        )
        assert next(sku for sku in discounted.skus if sku.id == first_sku_id).price == 900
        merchant_off = await set_merchant_product_sale_status(
            session, 2001, product_id, on_sale=False
        )
        assert merchant_off.status == ProductStatus.OFF_SHELF.value
        merchant_on = await set_merchant_product_sale_status(
            session, 2001, product_id, on_sale=True
        )
        assert merchant_on.status == ProductStatus.ON_SALE.value

        await update_product_audit_status(
            session,
            product_id,
            ProductStatus.OFF_SHELF.value,
            "Compliance review",
        )
        off_shelf = await get_product_audit_detail(session, product_id)
        assert off_shelf["status"] == ProductStatus.OFF_SHELF.value
        assert off_shelf["audit_reason"] == "Compliance review"


async def test_review_verifier_duplicate_and_summary(test_context, strong_password):
    client: AsyncClient = test_context["client"]
    ids = await seed_catalog(test_context["session_factory"])
    await seed_user(test_context["session_factory"], "13800138103", strong_password)
    headers = await login(client, "13800138103", strong_password)

    unavailable = await client.post(
        f"/products/{ids['cat_product_id']}/reviews",
        headers=headers,
        json={
            "order_item_id": 7001,
            "rating": 5,
            "content": "Great",
        },
    )
    assert unavailable.status_code == 409

    class FakeReviewPurchaseVerifier:
        async def verify(self, db, *, user_id: int, order_item_id: int):
            return ReviewPurchase(
                order_item_id=order_item_id,
                product_id=ids["cat_product_id"],
                sku_id=ids["cat_sku_id"],
            )

    app.dependency_overrides[get_review_purchase_verifier] = (
        lambda: FakeReviewPurchaseVerifier()
    )
    try:
        created = await client.post(
            f"/products/{ids['cat_product_id']}/reviews",
            headers=headers,
            json={
                "order_item_id": 7001,
                "rating": 5,
                "content": "Great",
                "is_anonymous": True,
            },
        )
        assert created.status_code == 200, created.text
        assert created.json()["user_id"] is None
        assert created.json()["sku_id"] == ids["cat_sku_id"]

        duplicate = await client.post(
            f"/products/{ids['cat_product_id']}/reviews",
            headers=headers,
            json={"order_item_id": 7001, "rating": 4},
        )
        assert duplicate.status_code == 409

        invalid_rating = await client.post(
            f"/products/{ids['cat_product_id']}/reviews",
            headers=headers,
            json={"order_item_id": 7002, "rating": 6},
        )
        assert invalid_rating.status_code == 422
    finally:
        app.dependency_overrides.pop(get_review_purchase_verifier, None)

    reviews = await client.get(
        f"/products/{ids['cat_product_id']}/reviews",
        params={"page": 1, "page_size": 10},
    )
    assert reviews.status_code == 200
    assert reviews.json()["total"] == 1
    assert reviews.json()["average_rating"] == 5.0


async def test_disabled_category_hides_product_and_invalidates_cart(
    test_context,
    strong_password,
):
    client: AsyncClient = test_context["client"]
    ids = await seed_catalog(test_context["session_factory"])
    await seed_user(test_context["session_factory"], "13800138104", strong_password)
    headers = await login(client, "13800138104", strong_password)

    added = await client.post(
        "/cart/items",
        headers=headers,
        json={"sku_id": ids["cat_sku_id"], "quantity": 1},
    )
    assert added.status_code == 200

    async with test_context["session_factory"]() as session:
        category = await session.get(ProductCategory, ids["cat_food_id"])
        category.is_enabled = False
        await session.commit()

    products = await client.get(
        "/products",
        params={"category_id": ids["cat_food_id"]},
    )
    assert products.status_code == 200
    assert products.json()["total"] == 0

    detail = await client.get(f"/products/{ids['cat_product_id']}")
    assert detail.status_code == 404

    cart = await client.get("/cart/items", headers=headers)
    assert cart.status_code == 200
    assert cart.json()[0]["available"] is False
