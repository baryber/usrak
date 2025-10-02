import time
from typing import TYPE_CHECKING

from sqlmodel import select
from sqlalchemy.orm import joinedload
from cachetools import TTLCache
from starlette.requests import HTTPConnection
from sqlmodel.ext.asyncio.session import AsyncSession

from usrak.core import enums
from usrak.core.security import decode_jwt_token
from usrak.core.security import hash_token
from usrak.remote_address import get_remote_address

if TYPE_CHECKING:
    from usrak.core.config_schemas import AppConfig, RouterConfig

from usrak.core.managers.tokens.auth import AuthTokensManager

TOKENS_USER_CACHE = TTLCache(maxsize=128, ttl=60)


async def resolve_user_from_access_token(
        access_token: str,
        session: AsyncSession,
        app_config: "AppConfig",
        router_config: "RouterConfig",
        tokens_manager: AuthTokensManager,
):
    User = router_config.USER_MODEL

    payload = decode_jwt_token(access_token, app_config.JWT_ACCESS_TOKEN_SECRET_KEY)
    if not payload or not payload.user_identifier:
        return None
    if payload.token_type == enums.TokenTypes.API_TOKEN:
        return None

    result = await session.exec(select(User).where(User.user_identifier == payload.user_identifier))
    user = result.first()
    if not user:
        return None

    await tokens_manager.validate_access_token(
        token=access_token,
        user_identifier=payload.user_identifier,
        password_version=user.password_version,
    )
    return user


async def resolve_user_from_api_token(
        connection: HTTPConnection,
        api_token: str,
        session: AsyncSession,
        app_config: "AppConfig",
        router_config: "RouterConfig",
):
    Tokens = router_config.TOKENS_MODEL

    hashed_token = hash_token(api_token)
    if hashed_token in TOKENS_USER_CACHE:
        Users = router_config.USER_MODEL
        id_field_name = getattr(Users, Users.__id_field_name__)
        user_id = TOKENS_USER_CACHE[hashed_token]
        result = await session.exec(select(Users).where(id_field_name == user_id))
        return result.first()

    owner_relation_field_name = router_config.TOKENS_OWNER_RELATION_FIELD_NAME
    token_from_db = await session.exec(
        select(Tokens).where(
            Tokens.token == hashed_token,
            Tokens.token_type == enums.TokenTypes.API_TOKEN,
            Tokens.is_deleted == False,
        ).options(
            joinedload(getattr(Tokens, owner_relation_field_name))
        )
    )
    token_obj = token_from_db.first()
    if not token_obj:
        return None

    user = getattr(token_obj, owner_relation_field_name)
    if not user:
        return None

    remote_addr = get_remote_address(connection)
    if remote_addr and token_obj.whitelisted_ip_addresses:
        if remote_addr not in token_obj.whitelisted_ip_addresses:
            return None

    if token_obj.expires_at:
        if token_obj.expires_at < int(time.time()):
            return None

        expires_in = token_obj.expires_at - int(time.time())
        if expires_in > app_config.API_TOKEN_RESOLVER_CACHE_TTL:
            TOKENS_USER_CACHE[hashed_token] = getattr(user, user.__id_field_name__)

    return user
