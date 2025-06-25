from typing import TYPE_CHECKING

from tenacity import retry, stop_after_attempt, wait_fixed

from .base import KeyValueStoreABS

if TYPE_CHECKING:
    from redis.asyncio import Redis


class RedisKeyValueStore(KeyValueStoreABS):
    def __init__(
            self,
            redis_cli: "Redis",
            key_prefix: str
    ):
        self.redis_cli = redis_cli
        self.key_prefix = key_prefix

    async def set(self, key: str, value, time: int = None):
        return await self.redis_cli.hset(
            self.key_prefix,
            key,
            value
        )

    async def get(self, key: str):
        return await self.redis_cli.hget(
            self.key_prefix,
            key
        )

    async def delete(self, key: str):
        return await self.redis_cli.delete(key)

    async def alive(self):
        return await self._ping()

    async def ttl(self, key: str):
        return await self.redis_cli.ttl(key)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), retry_error_callback=lambda _: False)
    async def _ping(self):
        await self.redis_cli.ping()
        return True
