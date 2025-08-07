from datetime import datetime, timezone, timedelta
from typing import Any

from usrak.core.logger import logger

from usrak.core import exceptions as exc
from usrak.core.schemas.security import JwtTokenPayloadData, SecretContext
from usrak.core.security import decode_jwt_token, create_jwt_token, verify_secret_context
from usrak.core.mixins import ConfigDependencyMixin


class TokensManagerBase(ConfigDependencyMixin):
    JTI_PREFIX = "jti"

    async def key_prefix(self, *args) -> str:
        """
        Generate a key prefix for the given object and user identifier.
        :param obj_prefix: The prefix for the object.
        :param user_identifier: The user identifier.
        :return: The generated key prefix.
        """
        return ":".join([str(arg) for arg in args])

    async def calculate_token_delta(self, exp: datetime) -> float:
        """
        Calculate the remaining time (in seconds) until the token expires.

        Args:
            exp (datetime): The expiration datetime of the token.

        Returns:
            float: The remaining time in seconds. Returns 0 if the token has expired.
        """
        current = datetime.now(timezone.utc)
        delta = (exp - current).total_seconds()
        return max(delta, 0)

    async def _verify_token_jti(
            self,
            user_identifier: Any,
            token_type: str,
            jti: str,
    ):
        """
        Verify if the token is blacklisted.
        :param token_type: The type of the token (e.g., access, refresh).
        :param user_identifier: The user identifier.
        :return: True if the token is blacklisted, False otherwise.
        """
        stored_jti = await self.kvs.hget(
            key=await self.key_prefix(self.JTI_PREFIX, token_type, user_identifier),
            field="0",
        )
        if not stored_jti:
            return False

        if stored_jti != jti:
            return False

        return True

    async def _set_token_jti(
            self,
            token_type: str,
            user_identifier: Any,
            jti: str,
            exp: int | float,
    ):
        """
        Set the token JTI in the key-value store.
        :param token_type: The type of the token (e.g., access, refresh).
        :param user_identifier: The user identifier.
        :param jti: The JTI of the token.
        :return: None
        """
        prefix = await self.key_prefix(self.JTI_PREFIX, token_type, user_identifier)
        await self.kvs.hset(
            key=prefix,
            field="0",
            value=jti,
        )
        await self.kvs.hexpire(
            key=prefix,
            ttl=exp,
        )

    async def _unset_token_jti(
            self,
            token_type: str,
            user_identifier: Any,
    ):
        """
        Delete the token JTI from the key-value store.
        :param token_type: The type of the token (e.g., access, refresh).
        :param user_identifier: The user identifier.
        :return: None
        """
        prefix = await self.key_prefix(self.JTI_PREFIX, token_type, user_identifier)
        await self.kvs.hdel(
            prefix,
            "0",
        )

    async def deactivate_token(
            self,
            token_type: str,
            user_identifier: Any,
    ):
        """
        Deactivate the token by deleting its JTI from the key-value store.
        :param token_type: The type of the token (e.g., access, refresh).
        :param user_identifier: The user identifier.
        :return: None
        """
        await self._unset_token_jti(token_type, user_identifier)

    async def create_token(
            self,
            token_type: str,
            user_identifier: Any,
            exp: int | float,
            jti: str,
            jwt_secret: str,
            secret_context: SecretContext | None = None,
    ):
        """
        Create a new JWT token.
        :param token_type: The type of the token (e.g., access, refresh).
        :param user_identifier:
        :param secret_context:
        :param jwt_secret:
        :param exp:
        :return:
        """
        exp_date = datetime.now(timezone.utc) + timedelta(seconds=exp)
        payload = JwtTokenPayloadData(
            token_type=token_type,
            user_identifier=user_identifier,
            secret_context=secret_context,
            exp=exp_date,
            jti=jti,
        )
        token = create_jwt_token(data=payload, jwt_secret=jwt_secret)
        logger.info(f"|{token_type}| token created for user: {user_identifier}")

        await self._set_token_jti(token_type=token_type, user_identifier=user_identifier, jti=jti, exp=exp)

        return token

    async def validate_token(
            self,
            token: str,
            jwt_secret: str,
            user_identifier: Any,
            secret_context: SecretContext | None = None
    ) -> JwtTokenPayloadData | None:
        """
        Validate the JWT token and check its JTI.
        :param token:
        :param jwt_secret:
        :param user_identifier:
        :param secret_context:
        :return:
        """

        payload = decode_jwt_token(token=token, jwt_secret=jwt_secret)
        if not payload:
            raise exc.InvalidTokenException

        if not await self._verify_token_jti(user_identifier, payload.token_type, payload.jti):
            raise exc.InvalidTokenException

        if payload.user_identifier != user_identifier:
            await self._unset_token_jti(payload.token_type, user_identifier)
            raise exc.InvalidTokenException

        if payload.secret_context:
            if not secret_context:
                await self._unset_token_jti(payload.token_type, user_identifier)
                raise exc.InvalidTokenException

            if not isinstance(secret_context, SecretContext) and not isinstance(payload.secret_context, SecretContext):
                await self._unset_token_jti(payload.token_type, user_identifier)
                raise exc.InvalidTokenException

            is_match = verify_secret_context(
                context=payload.secret_context,
                expected=secret_context
            )
            if not is_match:
                await self._unset_token_jti(payload.token_type, user_identifier)
                raise exc.InvalidTokenException

        return payload
