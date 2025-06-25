from usrak.core.logger import logger
from redis.asyncio import Redis

from usrak import config
from usrak.core import exceptions as exc, enums
from usrak.core._rate_limit import RedisRateLimiterBase as RLBase
from usrak.core.security import generate_6_digit_code, hash_6_digit_code, verify_6_digit_code


class MailCodeRateLimiter(RLBase):
    MAX_ATTEMPTS = config.MAX_MAIL_CREATE_CODE_ATTEMPTS
    TTL = config.MAIL_CODE_TTL

    def __init__(
            self,
            redis_prefix: str,
            redis_client: Redis,
    ):

        super().__init__(
            redis_client,
            redis_prefix,
            self.MAX_ATTEMPTS,
            self.TTL
        )

    async def create_code(
            self,
            user_identifier: str
    ):
        code = generate_6_digit_code()
        hashed = hash_6_digit_code(code)

        await self.create(
            user_identifier=user_identifier,
            hashed_obj=hashed,
            expires_in_seconds=config.EMAIL_VERIFICATION_LINK_EXPIRE_SEC,
            obj_type=enums.RateLimiterObjectType.CODE
        )

        return code

    async def verify_code(
            self,
            user_identifier: str,
            code: str
    ) -> bool:
        stored = await self.get(
            user_identifier=user_identifier,
            obj_type=enums.RateLimiterObjectType.CODE,
        )
        if not stored:
            raise exc.VerificationFailedException

        verify = verify_6_digit_code(plain_code=code, hashed_code=stored.value)
        if not verify:
            await self.handle_failed_attempt(user_identifier=user_identifier)
            logger.info(f"Mail code verification fail attempt, user ID: {user_identifier}")
            raise exc.InvalidVerificationCodeException

        return True
