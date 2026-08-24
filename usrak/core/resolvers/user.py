from typing import TYPE_CHECKING

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.requests import HTTPConnection

from usrak.core import enums
from usrak.core.managers.tokens.auth import AuthTokensManager
from usrak.core.resolvers.api_token import resolve_api_token_record
from usrak.core.security import decode_jwt_token
from usrak.remote_address import get_remote_address

if TYPE_CHECKING:
    from usrak.core.config_schemas import AppConfig, RouterConfig


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
    token_obj = await resolve_api_token_record(
        api_token=api_token,
        session=session,
        router_config=router_config,
        remote_addresses=(get_remote_address(connection),),
        load_owner=True,
    )
    if not token_obj:
        return None

    owner_relation_field_name = router_config.TOKENS_OWNER_RELATION_FIELD_NAME
    user = getattr(token_obj, owner_relation_field_name)
    if not user:
        return None
    return user
