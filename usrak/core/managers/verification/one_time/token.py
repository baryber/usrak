from typing import Optional
from datetime import timedelta, datetime, timezone

from usrak.core.managers.verification.one_time.base import OneTimeVerificationABS

from usrak.core.security import create_jwt_token
from usrak.core.security import encrypt_token
from usrak.core.schemas.security import JwtTokenPayloadData, SecretContext

from usrak import config, extension_config


class OneTimeTokenVerification(OneTimeVerificationABS[str]):
    def __init__(self, prefix: str):
        super().__init__(prefix)

        self.kvs = extension_config.KEY_VALUE_STORE

    async def _kvs_key(self, user_identifier: str):
        return f"{self.prefix}:{user_identifier}"

    async def create_secret(
            self,
            user_identifier: str,
            secret_context: Optional[SecretContext] = None
    ) -> str | None:
        token_expires = datetime.now(timezone.utc) + timedelta(seconds=config.ACCESS_TOKEN_EXPIRE_SEC)
        encode_data = JwtTokenPayloadData(
            user_identifier=user_identifier,
            exp=token_expires,
            secret_context=secret_context
        )
        token = create_jwt_token(data=encode_data)

        encrypted_token = encrypt_token(token=token)
        self.kvs.set()


