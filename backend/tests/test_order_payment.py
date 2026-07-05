import pytest
import base64
import json

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from models.order import Order, OrderStatus
from models.product import Product, ProductCategory, ProductSku
from main import app
from services.order_service import get_coin_reward_adapter, transition_fulfillment
from services.payment_service import _extract_signed_response
from settings.config import get_settings


pytestmark = pytest.mark.asyncio


class FakeRewardAdapter:
    def __init__(self):
        self.keys: list[str] = []

    async def grant_order_reward(
        self, *, user_id: int, order_id: int, pay_amount: int, idempotency_key: str
    ) -> None:
        self.keys.append(idempotency_key)


async def test_alipay_query_response_signature():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    body = {"code": "10000", "trade_status": "TRADE_SUCCESS", "trade_no": "T1"}
    content = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    signature = base64.b64encode(
        private_key.sign(content.encode(), padding.PKCS1v15(), hashes.SHA256())
    ).decode()
    payload = f'{{"alipay_trade_query_response":{content},"sign":"{signature}"}}'
    settings = get_settings()
    original = settings.alipay_public_key
    settings.alipay_public_key = public_pem
    try:
        verified, _ = _extract_signed_response(payload, "alipay_trade_query_response")
        assert verified["trade_no"] == "T1"
    finally:
        settings.alipay_public_key = original


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def register(client, cache, phone: str, password: str) -> str:
    await cache.set(f"sms:code:{phone}", "123456", ex=300)
    response = await client.post("/auth/register", json={
        "phone": phone, "password": password, "sms_code": "123456"
    })
    assert response.status_code == 200, response.text
    login = await client.post("/auth/login", json={"account": phone, "password": password})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


async def address(client, token: str) -> int:
    response = await client.post("/users/me/addresses", headers=auth(token), json={
        "receiver_name": "Buyer", "receiver_phone": "13800000000",
        "province": "P", "city": "C", "district": "D", "detail_address": "Road 1",
        "is_default": True,
    })
    return response.json()["id"]


async def seed_products(session_factory):
    async with session_factory() as db:
        category = ProductCategory(name="order-test", is_enabled=True)
        db.add(category)
        await db.flush()
        products = []
        for merchant, code in ((101, "ORDER-A"), (202, "ORDER-B")):
            product = Product(
                merchant_id=merchant, category_id=category.id, title=code,
                price=1000, stock=2, status="on_sale",
            )
            product.skus = [ProductSku(
                sku_code=code, name="default", specs={}, price=1000, stock=2, is_enabled=True
            )]
            db.add(product)
            products.append(product)
        await db.commit()
        return [product.skus[0].id for product in products]


async def test_cross_merchant_order_mock_payment_and_cancel(test_context, strong_password):
    client = test_context["client"]
    token = await register(client, test_context["cache"], "13920000001", strong_password)
    address_id = await address(client, token)
    sku_ids = await seed_products(test_context["session_factory"])
    cart_ids = []
    for sku_id in sku_ids:
        result = await client.post("/cart/items", headers=auth(token), json={"sku_id": sku_id, "quantity": 1})
        cart_ids.append(result.json()["id"])

    created = await client.post(
        "/orders", headers=auth(token),
        json={"address_id": address_id, "cart_item_ids": cart_ids},
    )
    assert created.status_code == 200, created.text
    assert len(created.json()) == 2
    assert {item["merchant_id"] for item in created.json()} == {101, 202}

    order_id = created.json()[0]["id"]
    payment = await client.post(f"/payments/orders/{order_id}/pay", headers=auth(token))
    repeated = await client.post(f"/orders/{order_id}/pay", headers=auth(token))
    assert payment.json()["out_trade_no"] == repeated.json()["out_trade_no"]
    trade_no = payment.json()["out_trade_no"]
    paid = await client.post(f"/payments/mock/{trade_no}/confirm", headers=auth(token))
    assert paid.json()["status"] == "paid"
    paid_again = await client.post(f"/payments/mock/{trade_no}/confirm", headers=auth(token))
    assert paid_again.json()["status"] == "paid"

    cancel_id = created.json()[1]["id"]
    cancel_payment = await client.post(f"/payments/orders/{cancel_id}/pay", headers=auth(token))
    cancelled = await client.post(f"/orders/{cancel_id}/cancel", headers=auth(token))
    assert cancelled.json()["status"] == "cancelled"
    cancelled_confirm = await client.post(
        f"/payments/mock/{cancel_payment.json()['out_trade_no']}/confirm", headers=auth(token)
    )
    assert cancelled_confirm.status_code == 409
    async with test_context["session_factory"]() as db:
        order = await db.get(Order, order_id)
        assert order.status == OrderStatus.PAID.value
        await transition_fulfillment(db, order_id, OrderStatus.PENDING_SHIPMENT.value)
        await transition_fulfillment(db, order_id, OrderStatus.SHIPPED.value)
        await transition_fulfillment(db, order_id, OrderStatus.PENDING_RECEIPT.value)
    rewards = FakeRewardAdapter()
    app.dependency_overrides[get_coin_reward_adapter] = lambda: rewards
    completed = await client.post(f"/orders/{order_id}/confirm-receipt", headers=auth(token))
    assert completed.json()["status"] == "completed"
    duplicate = await client.post(f"/orders/{order_id}/confirm-receipt", headers=auth(token))
    assert duplicate.status_code == 409
    assert rewards.keys == [f"order:{order_id}:receipt_reward"]
    invalid_notify = await client.post("/payments/alipay/notify", data={"sign": "invalid"})
    assert invalid_notify.status_code == 400


async def test_order_owner_isolation(test_context, strong_password):
    client = test_context["client"]
    token_a = await register(client, test_context["cache"], "13920000002", strong_password)
    token_b = await register(client, test_context["cache"], "13920000003", strong_password)
    address_id = await address(client, token_a)
    sku_id = (await seed_products(test_context["session_factory"]))[0]
    cart = await client.post("/cart/items", headers=auth(token_a), json={"sku_id": sku_id, "quantity": 1})
    order = await client.post("/orders", headers=auth(token_a), json={
        "address_id": address_id, "cart_item_ids": [cart.json()["id"]]
    })
    order_id = order.json()[0]["id"]
    assert (await client.get(f"/orders/{order_id}", headers=auth(token_b))).status_code == 404
