from httpx import AsyncClient
import pytest

from core.auth import hash_password
from models.user import User


pytestmark = pytest.mark.asyncio


async def seed_sms_code(cache, phone: str, code: str = "123456") -> None:
    await cache.set(f"sms:code:{phone}", code, ex=300)


async def register_user(client: AsyncClient, cache, phone: str, password: str) -> dict:
    await seed_sms_code(cache, phone)
    response = await client.post(
        "/auth/register",
        json={
            "phone": phone,
            "password": password,
            "sms_code": "123456",
            "nickname": "tester",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


async def login_user(client: AsyncClient, phone: str, password: str) -> str:
    response = await client.post(
        "/auth/login",
        json={"account": phone, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_send_sms_code_validation_cooldown_and_cache(test_context):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]

    invalid = await client.post("/auth/code", json={"phone": "123"})
    assert invalid.status_code == 422

    response = await client.post("/auth/code", json={"phone": "13800138000"})
    assert response.status_code == 200, response.text
    assert response.json()["debug_code"] is None
    assert await cache.get("sms:code:13800138000") == "123456"
    assert cache.expires["sms:code:13800138000"] == 300

    duplicate = await client.post("/auth/code", json={"phone": "13800138000"})
    assert duplicate.status_code == 429


async def test_register_login_profile_and_password_token_version(test_context, strong_password):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]

    user = await register_user(client, cache, "13800138001", strong_password)
    assert user["phone"] == "13800138001"

    await seed_sms_code(cache, "13800138001")
    duplicate = await client.post(
        "/auth/register",
        json={
            "phone": "13800138001",
            "password": strong_password,
            "sms_code": "123456",
        },
    )
    assert duplicate.status_code == 409

    token = await login_user(client, "13800138001", strong_password)
    me = await client.get("/users/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["phone"] == "13800138001"

    updated = await client.put(
        "/users/me/profile",
        headers=auth_headers(token),
        json={
            "nickname": "new-name",
            "city": "Shanghai",
            "pet_experience": "newbie",
            "living_environment": "apartment",
        },
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["nickname"] == "new-name"
    assert body["profile"]["pet_experience"] == "newbie"

    changed = await client.post(
        "/users/me/change-password",
        headers=auth_headers(token),
        json={"old_password": strong_password, "new_password": "NewPassw0rd!"},
    )
    assert changed.status_code == 200

    old_token_result = await client.get("/users/me", headers=auth_headers(token))
    assert old_token_result.status_code == 401

    new_token = await login_user(client, "13800138001", "NewPassw0rd!")
    assert new_token != token


async def test_disabled_users_cannot_login(test_context, strong_password):
    client: AsyncClient = test_context["client"]
    session_factory = test_context["session_factory"]

    async with session_factory() as session:
        frozen = User(
            phone="13800138002",
            password_hash=hash_password(strong_password),
            is_frozen=True,
        )
        deleted = User(
            phone="13800138003",
            password_hash=hash_password(strong_password),
            is_deleted=True,
        )
        session.add_all([frozen, deleted])
        await session.commit()

    frozen_login = await client.post(
        "/auth/login",
        json={"account": "13800138002", "password": strong_password},
    )
    assert frozen_login.status_code == 401

    deleted_login = await client.post(
        "/auth/login",
        json={"account": "13800138003", "password": strong_password},
    )
    assert deleted_login.status_code == 401


async def test_address_default_delete_and_owner_isolation(test_context, strong_password):
    client: AsyncClient = test_context["client"]
    cache = test_context["cache"]

    await register_user(client, cache, "13800138004", strong_password)
    token_a = await login_user(client, "13800138004", strong_password)

    await register_user(client, cache, "13800138005", strong_password)
    token_b = await login_user(client, "13800138005", strong_password)

    first = await client.post(
        "/users/me/addresses",
        headers=auth_headers(token_a),
        json={
            "receiver_name": "A",
            "receiver_phone": "13800138004",
            "province": "Zhejiang",
            "city": "Hangzhou",
            "district": "Xihu",
            "detail_address": "No.1",
        },
    )
    assert first.status_code == 200, first.text
    first_id = first.json()["id"]
    assert first.json()["is_default"] is True

    second = await client.post(
        "/users/me/addresses",
        headers=auth_headers(token_a),
        json={
            "receiver_name": "A2",
            "receiver_phone": "13800138004",
            "province": "Zhejiang",
            "city": "Hangzhou",
            "district": "Xihu",
            "detail_address": "No.2",
            "is_default": True,
        },
    )
    assert second.status_code == 200, second.text
    second_id = second.json()["id"]
    assert second.json()["is_default"] is True

    addresses = await client.get("/users/me/addresses", headers=auth_headers(token_a))
    assert addresses.status_code == 200
    defaults = [item for item in addresses.json() if item["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["id"] == second_id

    owner_isolation = await client.put(
        f"/users/me/addresses/{first_id}",
        headers=auth_headers(token_b),
        json={"receiver_name": "bad"},
    )
    assert owner_isolation.status_code == 404

    deleted = await client.delete(
        f"/users/me/addresses/{second_id}",
        headers=auth_headers(token_a),
    )
    assert deleted.status_code == 200

    after_delete = await client.get("/users/me/addresses", headers=auth_headers(token_a))
    assert after_delete.status_code == 200
    assert len(after_delete.json()) == 1
    assert after_delete.json()[0]["id"] == first_id
    assert after_delete.json()[0]["is_default"] is True
