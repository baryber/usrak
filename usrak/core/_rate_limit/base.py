import json
from typing import Optional
from datetime import datetime, timezone

from usrak.core.logger import logger
from tenacity import retry, stop_after_attempt, wait_fixed

from usrak.core import exceptions as exc, enums
from usrak.core.schemas.redis import RateLimitObj

try:
    from redis.asyncio import Redis, RedisError
except ImportError:
    Redis = None
    RedisError = None


class RedisRateLimiterBase:
    def __new__(cls, *args, **kwargs):
        if Redis is None or RedisError is None:
            raise ImportError("Redis client is not available. Please install 'redis' package.")

    def __init__(
            self,
            redis_client: Redis,
            redis_prefix: str,
            max_attempts: int,
            key_ttl: int
    ):
        self.redis = redis_client
        self.prefix = redis_prefix

        self.max_attempts = max_attempts
        self.ttl = key_ttl

    def _redis_key(self, user_identifier: str):
        return f"{self.prefix}:{user_identifier}"

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def _is_redis_available(self) -> bool:
        await self.redis.ping()
        return True

    async def get_create_wait_time(self, user_identifier: str) -> int:
        try:
            key = self._redis_key(user_identifier)
            async with self.redis.pipeline() as pipe:
                await pipe.hget(key, "create_blocked")
                await pipe.ttl(key)
                create_blocked, ttl = await pipe.execute()

            return max(ttl, 0) if create_blocked else 0

        except RedisError as e:
            logger.error(f"Redis error in get_create_wait_time: {e}")
            return 0

    async def get_verify_wait_time(self, user_identifier: str) -> int:
        try:
            key = self._redis_key(user_identifier)
            async with self.redis.pipeline() as pipe:
                await pipe.hget(key, "verify_blocked")
                await pipe.ttl(key)
                verify_blocked, ttl = await pipe.execute()

            return max(ttl, 0) if verify_blocked else 0

        except RedisError as e:
            logger.error(f"Redis error in get_verify_wait_time: {e}")
            return 0

    async def create(
            self,
            user_identifier: str,
            hashed_obj: str,
            expires_in_seconds: int,
            obj_type: enums.RateLimiterObjectType
    ):
        obj_type = obj_type.value
        key = self._redis_key(user_identifier)

        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                await pipe.hgetall(key)
                data_list = await pipe.execute()
                data = data_list[0] or {}

                if data.get("create_blocked"):
                    wait_time = await self.get_create_wait_time(user_identifier)
                    raise exc.MailSendRateLimitException(wait_time)

                current_objs = sum(1 for k in data.keys() if k.startswith(f"{obj_type}:"))
                if current_objs >= self.max_attempts:
                    await pipe.hset(key, "create_blocked", "1")
                    await pipe.expire(key, self.ttl)
                    await pipe.execute()
                    raise exc.MailSendRateLimitException(self.ttl)

                try:
                    obj_data = RateLimitObj(
                        value=hashed_obj,
                        created_at=datetime.now(timezone.utc).isoformat()
                    )

                except (TypeError, ValueError) as e:
                    logger.error(f"JSON serialization error: {e}")
                    # TODO: replace with custom exc
                    raise ValueError("Invalid object data")

                await pipe.hset(key, f"{obj_type}:{current_objs}", obj_data.model_dump_json())
                await pipe.expire(key, expires_in_seconds)
                await pipe.execute()

        except RedisError as e:
            logger.error(f"Redis error in create: {e}")
            raise exc.RedisOperationFailedException

    async def _get_obj(self, user_identifier: str) -> dict:
        try:
            key = self._redis_key(user_identifier)
            data = await self.redis.hgetall(key) or {}
            if not data:
                raise exc.VerificationFailedException

            if data.get("verify_blocked"):
                wait_time = await self.get_verify_wait_time(user_identifier)
                raise exc.MailSendRateLimitException(wait_time)

            return data

        except RedisError as e:
            logger.error(f"Redis error in _get_obj: {e}")
            raise exc.RedisOperationFailedException

    async def _get_obj_latest_value(
            self,
            obj_data: dict,
            obj_type: enums.RateLimiterObjectType
    ) -> Optional[dict]:
        latest_value = None
        latest_index = -1
        for field, value in obj_data.items():
            if field.startswith(f"{obj_type.value}:"):

                try:
                    index = int(field.split(":")[1])
                    if index > latest_index:
                        latest_index = index
                        latest_value = json.loads(value)

                except (ValueError, json.JSONDecodeError) as e:
                    logger.warning(f"Invalid field format or JSON: {field}, error: {e}")
                    continue

        return latest_value

    async def handle_failed_attempt(self, user_identifier: str):
        key = self._redis_key(user_identifier)
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                await pipe.hget(key, "verify_blocked")
                await pipe.hget(key, "failed_attempts")
                verify_blocked, failed_attempts = await pipe.execute()
                failed_attempts = int(failed_attempts or 0)

                if verify_blocked:
                    wait_time = await self.get_verify_wait_time(user_identifier)
                    raise exc.MailSendRateLimitException(wait_time)

                failed_attempts += 1
                await pipe.hset(key, "failed_attempts", str(failed_attempts))
                if failed_attempts >= self.max_attempts:
                    await pipe.hset(key, "verify_blocked", "1")
                    await pipe.expire(key, self.ttl)

                await pipe.execute()

                if failed_attempts >= self.max_attempts:
                    raise exc.MailSendRateLimitException(self.ttl)

        except RedisError as e:
            logger.error(f"Redis error in handle_failed_attempt: {e}")
            raise exc.RedisOperationFailedException

    async def get(
            self,
            user_identifier: str,
            obj_type: enums.RateLimiterObjectType
    ) -> Optional[RateLimitObj]:
        try:
            data = await self._get_obj(user_identifier)
            latest_value = await self._get_obj_latest_value(data, obj_type)
            if not latest_value:
                await self.handle_failed_attempt(user_identifier)
                logger.info(f"Latest code not found, user ID: {user_identifier}")
                raise exc.VerificationFailedException

            return RateLimitObj(**latest_value)

        except RedisError as e:
            logger.error(f"Redis error in verify: {e}")
            raise exc.RedisOperationFailedException

    async def cleanup(self, user_identifier: str) -> None:
        try:
            if not await self._is_redis_available():
                return

            key = self._redis_key(user_identifier)
            async with self.redis.pipeline() as pipe:
                await pipe.hget(key, "create_blocked")
                await pipe.hget(key, "verify_blocked")
                create_blocked, verify_blocked = await pipe.execute()

            if not create_blocked and not verify_blocked:
                await self.redis.delete(key)

        except RedisError as e:
            logger.error(f"Redis error in cleanup: {e}")
