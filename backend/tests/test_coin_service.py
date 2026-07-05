from httpx import AsyncClient
import pytest
from sqlalchemy import func, select

from models.coin import PetCoinAccount, PetCoinLog
from services.coin_service import deduct_coin, grant_coin


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


async def test_coin_account_checkin_logs_and_tasks(test_context, strong_password):
    client: AsyncClient = test_context["client"]
    token = await register(client, test_context["cache"], "13940000001", strong_password)

    account = await client.get("/coins/account", headers=auth(token))
    assert account.status_code == 200, account.text
    assert account.json()["balance"] == 0

    checkin = await client.post("/coins/checkin", headers=auth(token))
    assert checkin.status_code == 200, checkin.text
    assert checkin.json()["reward_amount"] == 10
    assert checkin.json()["account"]["balance"] == 10

    duplicate = await client.post("/coins/checkin", headers=auth(token))
    assert duplicate.status_code == 409

    logs = await client.get("/coins/logs", headers=auth(token))
    assert logs.status_code == 200
    assert logs.json()[0]["balance_before"] == 0
    assert logs.json()[0]["balance_after"] == 10

    tasks = await client.get("/coins/tasks", headers=auth(token))
    assert tasks.status_code == 200, tasks.text
    task_id = tasks.json()[0]["id"]
    claimed = await client.post(f"/coins/tasks/{task_id}/claim", headers=auth(token))
    assert claimed.status_code == 200, claimed.text
    assert claimed.json()["account"]["balance"] > 10
    duplicate_claim = await client.post(f"/coins/tasks/{task_id}/claim", headers=auth(token))
    assert duplicate_claim.status_code == 409


async def test_coin_service_idempotency_and_insufficient_balance(test_context):
    session_factory = test_context["session_factory"]
    async with session_factory() as db:
        db.add(PetCoinAccount(user_id=99))
        await db.commit()

        await grant_coin(db, 99, 50, "order_reward", related_id=1, idempotency_key="order:1:receipt_reward")
        await grant_coin(db, 99, 50, "order_reward", related_id=1, idempotency_key="order:1:receipt_reward")
        await db.commit()
        account = await db.get(PetCoinAccount, 1)
        assert account.balance == 50
        log_count = await db.scalar(
            select(func.count(PetCoinLog.id)).where(
                PetCoinLog.idempotency_key == "order:1:receipt_reward"
            )
        )
        assert log_count == 1

        await deduct_coin(db, 99, 30, "coin_deduct", related_id=1, idempotency_key="deduct:1")
        await db.commit()
        await db.refresh(account)
        assert account.balance == 20

        with pytest.raises(Exception):
            await deduct_coin(db, 99, 30, "coin_deduct", related_id=2, idempotency_key="deduct:2")
