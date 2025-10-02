import time
from typing import Optional
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from usrak.core.logger import logger

from usrak.core import exceptions as exc, enums
from usrak.core.security import generate_jti
from usrak.core.schemas.security import SecretContext
from usrak.core.managers.tokens.base import TokensManagerBase
from usrak.core.dependencies.config_provider import get_app_config
from usrak.core.dependencies.managers import get_tokens_model

from usrak.core.security import hash_token, create_secret_token


class AuthTokensManager(TokensManagerBase):
    """
    AuthTokensManager is responsible for managing authentication tokens.
    It handles the generation, validation, and blacklisting of access and refresh tokens.
    """
    JTI_PREFIX = "jti"
    ACCESS_TOKEN_PREFIX = "access_token"
    REFRESH_TOKEN_PREFIX = "refresh_token"

    async def create_access_token(
            self,
            user_identifier: str,
            password_version: int,
    ) -> str:
        jti = generate_jti()
        expires_at = int(time.time()) + self.app_config.ACCESS_TOKEN_EXPIRE_SEC
        token = await self.create_token(
            token_type=enums.TokenTypes.ACCESS.value,
            user_identifier=user_identifier,
            expires_at=expires_at,
            jti=jti,
            jwt_secret=self.app_config.JWT_ACCESS_TOKEN_SECRET_KEY,
            secret_context=SecretContext(
                password_version=password_version
            ),
        )
        jti_prefix = await self.key_prefix(self.JTI_PREFIX, self.ACCESS_TOKEN_PREFIX, user_identifier)
        await self.kvs.hset(
            key=jti_prefix,
            field="0",
            value=jti,
        )
        await self.kvs.hexpire(
            key=jti_prefix,
            ttl=self.app_config.ACCESS_TOKEN_EXPIRE_SEC,
        )

        return token

    async def create_refresh_token(
            self,
            user_identifier: str,
            password_version: int,
    ) -> str:
        jti = generate_jti()
        expires_at = int(time.time()) + self.app_config.REFRESH_TOKEN_EXPIRE_SEC
        token = await self.create_token(
            token_type=enums.TokenTypes.REFRESH.value,
            user_identifier=user_identifier,
            expires_at=expires_at,
            jti=jti,
            jwt_secret=self.app_config.JWT_REFRESH_TOKEN_SECRET_KEY,
            secret_context=SecretContext(
                password_version=password_version
            ))

        jti_prefix = await self.key_prefix(self.JTI_PREFIX, self.REFRESH_TOKEN_PREFIX, user_identifier)
        await self.kvs.hset(
            key=jti_prefix,
            field="0",
            value=jti,
        )
        await self.kvs.hexpire(
            key=jti_prefix,
            ttl=self.app_config.REFRESH_TOKEN_EXPIRE_SEC,
        )

        return token

    async def create_api_token(
            self,
            user_identifier: str,
            session: AsyncSession,
            name: Optional[str] = None,
            expires_at: Optional[int] = None,
            whitelisted_ip_addresses: Optional[list[str]] = None,
    ) -> str:
        app_config = get_app_config()
        Tokens = get_tokens_model()

        stmt = select(func.count()).select_from(Tokens).where(
            Tokens.owner_identifier == user_identifier,
            Tokens.token_type == enums.TokenTypes.API_TOKEN.value,
            Tokens.is_deleted == False,
        )

        count: int = await session.scalar(stmt)
        if count >= app_config.MAX_API_TOKENS_PER_USER:
            raise exc.TooManyAPIKeysException(max_keys=app_config.MAX_API_TOKENS_PER_USER)

        token = create_secret_token()

        hashed_token = hash_token(token)

        token_model = Tokens(
            **{Tokens.__owner_field_name__: user_identifier},
            name=name,
            token=hashed_token,
            token_type=enums.TokenTypes.API_TOKEN.value,
            expires_at=expires_at,
            whitelisted_ip_addresses=whitelisted_ip_addresses,
            is_deleted=False,
        )
        session.add(token_model)
        await session.commit()

        return token

    async def delete_api_token(
            self,
            token_identifier: str,
            user_identifier: str,
            session: AsyncSession,
    ) -> None:
        tokens_model = get_tokens_model()

        owner_col = getattr(tokens_model, tokens_model.__owner_field_name__)

        stmt = select(tokens_model).where(
            owner_col == user_identifier,
            tokens_model.token_identifier == token_identifier,
            tokens_model.token_type == enums.TokenTypes.API_TOKEN.value,
            tokens_model.is_deleted == False,
        )
        result = await session.exec(stmt)
        token_obj = result.first()
        if not token_obj:
            raise exc.InvalidTokenException

        token_obj.is_deleted = True
        session.add(token_obj)
        await session.commit()

    async def validate_api_token(
            self,
            token: str,
            user_identifier: str,
            session: AsyncSession,
            whitelisted_ip_addresses: Optional[list[str]] = None
    ) -> None:
        await self.validate_token(
            token=token,
            jwt_secret=self.app_config.JWT_API_TOKEN_SECRET_KEY,
            user_identifier=user_identifier,
            secret_context=SecretContext(ip_addresses=whitelisted_ip_addresses) if whitelisted_ip_addresses else None
        )
        tokens_model = get_tokens_model()

        hashed_token = hash_token(token)

        owner_col = getattr(tokens_model, tokens_model.__owner_field_name__)

        stmt = select(tokens_model).where(
            owner_col == user_identifier,
            tokens_model.token == hashed_token,
            tokens_model.token_type == enums.TokenTypes.API_TOKEN.value,
            tokens_model.is_deleted == False,
        )

        result = await session.exec(stmt)
        maybe_obj = result.one_or_none()

        if maybe_obj is None:
            raise exc.InvalidTokenException

        token_obj = maybe_obj if isinstance(maybe_obj, tokens_model) else maybe_obj[0]

        if not token_obj:
            raise exc.InvalidTokenException

    async def validate_access_token(
            self,
            token: str,
            password_version: int,
            user_identifier: str
    ) -> None:
        await self.validate_token(
            token=token,
            jwt_secret=self.app_config.JWT_ACCESS_TOKEN_SECRET_KEY,
            user_identifier=user_identifier,
            secret_context=SecretContext(
                password_version=password_version
            )
        )

    async def handle_refresh_token(
            self,
            refresh_token: str,
            user_identifier: str,
            password_version: int,
            old_access_token: str | None = None
    ) -> str:
        payload = await self.validate_token(
            token=refresh_token,
            jwt_secret=self.app_config.JWT_REFRESH_TOKEN_SECRET_KEY,
            user_identifier=user_identifier,
            secret_context=SecretContext(
                password_version=password_version
            )
        )

        await self.deactivate_token(
            token_type=enums.TokenTypes.REFRESH.value,
            user_identifier=user_identifier
        )

        if old_access_token:
            await self.deactivate_token(
                token_type=enums.TokenTypes.ACCESS.value,
                user_identifier=user_identifier
            )

        if not payload.secret_context or not payload.secret_context.password_version:
            logger.warning(
                "Password version is not provided in the refresh token secret context. "
                "Please check the token generation process."
            )
            await self.terminate_all_user_sessions(user_identifier)
            raise exc.InvalidTokenException

        secret_context = SecretContext(
            password_version=payload.secret_context.password_version
        )
        new_refresh_token = await self.create_refresh_token(
            user_identifier=user_identifier,
            password_version=secret_context.password_version,
        )

        return new_refresh_token

    async def terminate_all_user_sessions(self, user_identifier: str) -> None:
        """
        Terminate all user sessions by deleting all tokens associated with the user.
        """
        await self.deactivate_token(
            token_type=enums.TokenTypes.ACCESS.value,
            user_identifier=user_identifier
        )

        await self.deactivate_token(
            token_type=enums.TokenTypes.REFRESH.value,
            user_identifier=user_identifier
        )
