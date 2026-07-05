import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.cache import get_cache
from core.dependencies import get_db
from main import app
from models import Base
from services.sms_service import SmsSendResult, get_sms_service


class InMemoryCache:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.expires: dict[str, int | None] = {}

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.values[key] = value
        self.expires[key] = ex

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def delete(self, key: str) -> None:
        self.values.pop(key, None)
        self.expires.pop(key, None)


class FakeSmsService:
    def __init__(self, code: str = "123456") -> None:
        self.code = code

    def send_verify_code(self, phone: str) -> SmsSendResult:
        return SmsSendResult(success=True, message="sent", code=self.code)


@pytest_asyncio.fixture
async def test_context() -> AsyncIterator[dict]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    cache = InMemoryCache()

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    def override_get_cache() -> InMemoryCache:
        return cache

    def override_get_sms_service() -> FakeSmsService:
        return FakeSmsService()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_cache] = override_get_cache
    app.dependency_overrides[get_sms_service] = override_get_sms_service

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield {
            "client": client,
            "cache": cache,
            "session_factory": session_factory,
        }

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture
def strong_password() -> str:
    return "Passw0rd!123"
