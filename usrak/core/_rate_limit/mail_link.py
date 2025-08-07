from datetime import timedelta, datetime, timezone

from usrak.core.logger import logger
from redis.asyncio import Redis

from usrak import config
from usrak.core import exceptions as exc, enums
from usrak.core.schemas.security import PasswordResetTokenEncodeData
from app.src import auth_manager
from usrak.core._rate_limit import RedisRateLimiterBase as RLBase
from usrak.core.security import encrypt_token, decrypt_token
from usrak.core.security import create_password_reset_token


class MailLinkRateLimiter(RLBase):
    MAX_ATTEMPTS = config.MAX_MAIL_CREATE_LINK_ATTEMPTS
    TTL = config.MAIL_LINK_TTL

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

    async def create_link(
            self,
            user_identifier: str,
            password_version: int
    ):
        token_expires = datetime.now(timezone.utc) + timedelta(seconds=config.ACCESS_TOKEN_EXPIRE_SEC)
        encode_data = PasswordResetTokenEncodeData(
            user_identifier=user_identifier,
            password_version=password_version,
            exp=token_expires
        )

        token = create_password_reset_token(
            data=encode_data,
        )
        encrypted = encrypt_token(token)

        await self.create(
            user_identifier=user_identifier,
            hashed_obj=encrypted,
            expires_in_seconds=config.PASSWORD_RESET_LINK_EXPIRE_SEC,
            obj_type=enums.RateLimiterObjectType.LINK
        )
        return token

    async def verify_link(
            self,
            user_identifier: str,
            password_version: int,
            token: str
    ) -> bool:
        stored = await self.get(
            user_identifier=user_identifier,
            obj_type=enums.RateLimiterObjectType.LINK
        )
        if not stored:
            raise exc.VerificationFailedException

        decrypted = decrypt_token(stored.value)
        if decrypted != token:
            await self.handle_failed_attempt(user_identifier=user_identifier)
            logger.info(f"Mail link verification fail attempt, user ID: {user_identifier}")
            raise exc.InvalidTokenException

        valid = await auth_manager.validate_reset_password_token(
            token=token,
            user_identifier=user_identifier,
            password_version=password_version
        )


        return False if not valid else True

