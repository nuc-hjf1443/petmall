from httpx import AsyncClient
import pytest


pytestmark = pytest.mark.asyncio


async def seed_sms_code(cache, phone: str, code: str = "123456") -> None:
    await cache.set(f"sms:code:{phone}", code, ex=300)


async def register(client: AsyncClient, cache, phone: str, password: str) -> str:
    await seed_sms_code(cache, phone)
    response = await client.post(
        "/auth/register",
        json={"phone": phone, "password": password, "sms_code": "123456"},
    )
    assert response.status_code == 200, response.text
    login = await client.post("/auth/login", json={"account": phone, "password": password})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_pet_profile_records_reminders_detail_and_preview(test_context, strong_password):
    client: AsyncClient = test_context["client"]
    token = await register(client, test_context["cache"], "13930000001", strong_password)

    await client.put(
        "/users/me/profile",
        headers=auth(token),
        json={
            "nickname": "pet-owner",
            "city": "Shanghai",
            "pet_experience": "newbie",
            "living_environment": "apartment",
            "budget_preference": "medium",
        },
    )

    created = await client.post(
        "/pets",
        headers=auth(token),
        json={
            "name": "Mimi",
            "pet_type": "cat",
            "breed": "British Shorthair",
            "gender": "female",
            "weight": 4.2,
            "vaccine_status": "done",
            "deworm_status": "done",
        },
    )
    assert created.status_code == 200, created.text
    pet_id = created.json()["id"]

    record = await client.post(
        f"/pets/{pet_id}/growth-records",
        headers=auth(token),
        json={"record_type": "weight", "title": "monthly weight", "content": "4.2kg", "weight": 4.2},
    )
    assert record.status_code == 200, record.text

    reminder = await client.post(
        f"/pets/{pet_id}/reminders",
        headers=auth(token),
        json={
            "reminder_type": "vaccine",
            "title": "next vaccine",
            "due_at": "2026-08-01T10:00:00+00:00",
            "notes": "call clinic",
        },
    )
    assert reminder.status_code == 200, reminder.text

    detail = await client.put(
        f"/pets/{pet_id}/detail-profile",
        headers=auth(token),
        json={
            "body_size": "medium",
            "health_notes": "healthy",
            "allergy_notes": "no chicken",
            "diet_preference": "wet food",
            "product_preference": "low dust litter",
            "behavior_notes": "shy",
            "care_notes": "brush weekly",
        },
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["profile_completeness"] > 80

    completeness = await client.get(f"/pets/{pet_id}/profile-completeness", headers=auth(token))
    assert completeness.status_code == 200
    assert completeness.json()["completeness"] > 80

    preview = await client.post(f"/pets/{pet_id}/profile-document/preview", headers=auth(token))
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert "用户养宠背景" in body["content"]
    assert "宠物基础信息" in body["content"]
    assert body["source_snapshot"]["pet"]["id"] == pet_id


async def test_pet_owner_isolation(test_context, strong_password):
    client: AsyncClient = test_context["client"]
    token_a = await register(client, test_context["cache"], "13930000002", strong_password)
    token_b = await register(client, test_context["cache"], "13930000003", strong_password)

    created = await client.post(
        "/pets",
        headers=auth(token_a),
        json={"name": "Lucky", "pet_type": "dog"},
    )
    assert created.status_code == 200, created.text
    pet_id = created.json()["id"]

    assert (await client.get(f"/pets/{pet_id}", headers=auth(token_b))).status_code == 404
    assert (
        await client.post(
            f"/pets/{pet_id}/growth-records",
            headers=auth(token_b),
            json={"record_type": "weight"},
        )
    ).status_code == 404
    assert (
        await client.put(
            f"/pets/{pet_id}/detail-profile",
            headers=auth(token_b),
            json={"body_size": "small"},
        )
    ).status_code == 404
