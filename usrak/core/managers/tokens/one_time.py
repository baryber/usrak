from usrak.core import exceptions as exc
from usrak.core.managers.tokens.base import TokensManagerBase


class OneTimeTokensManager(TokensManagerBase):
    ONETIME_TOKEN_PREFIX = "onetime_token"
    CREATE_BLOCKED_FIELD = "create_blocked"
    VERIFY_BLOCKED_FIELD = "verify_blocked"

    async def __key_prefix(self, user_identifier: str) -> str:
        """
        Generate a key prefix for the token based on the user identifier.
        """
        return f"{self.ONETIME_TOKEN_PREFIX}:{user_identifier}"

    async def set_blocked_flag(
            self,
            user_identifier: str,
            flag: str,
            ttl: int | float | None
    ):
        """
        Set a flag to block the creation of new tokens for the user.
        """

        if ttl is None:
            ttl = self.kvs.default_ttl

        await self.kvs.hset(
            key=self.__key_prefix(user_identifier),
            field=flag,
            value="1"
        )
        await self.kvs.hexpire(
            key=self.__key_prefix(user_identifier),
            ttl=ttl
        )

    async def get_create_wait_time(self, user_identifier: str) -> int:
        """
        Get the wait time for creating a new token for the user.
        """
        key = self.__key_prefix(user_identifier)
        data = await self.kvs.hgetall(key) or {}
        ttl = await self.kvs.httl(key) or 0

        create_blocked = data.get(self.CREATE_BLOCKED_FIELD)
        verify_blocked = data.get(self.VERIFY_BLOCKED_FIELD)
        if create_blocked:
            return max(ttl, 0)
        elif verify_blocked:
            return max(ttl, 0)
        else:
            return 0

    async def create_one_time_token(
            self,
            user_identifier: str,
            exp: int | float,
            password_version: int,
            purpose: str
    ) -> str:
        key = self.__key_prefix(user_identifier)
        data = self.kvs.hgetall(key) or {}
        if data.get(self.CREATE_BLOCKED_FIELD):
            wait_time = await self.get_create_wait_time(user_identifier)
            raise exc.MailSendRateLimitException(wait_time)

        current_objs = sum(1 for k in data.keys() if k.startswith(f"{self.ONETIME_TOKEN_PREFIX}:"))




