from typing import Protocol

import redis.asyncio as redis

from settings.config import get_settings


class CacheBackend(Protocol):
    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        ...

    async def get(self, key: str) -> str | None:
        ...

    async def delete(self, key: str) -> None:
        ...


class RedisCache:
    def __init__(self, client: redis.Redis) -> None:
        self.client = client

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        await self.client.set(key, value, ex=ex)

    async def get(self, key: str) -> str | None:
        value = await self.client.get(key)
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    async def delete(self, key: str) -> None:
        await self.client.delete(key)


_redis_cache: RedisCache | None = None


def get_cache() -> CacheBackend:
    global _redis_cache
    if _redis_cache is None:
        settings = get_settings()
        client = redis.from_url(settings.redis_url, decode_responses=True)
        _redis_cache = RedisCache(client)
    return _redis_cache
