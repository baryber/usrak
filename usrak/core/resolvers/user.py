from fastapi import Request
from typing import TYPE_CHECKING
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from usrak.core import enums
from usrak.core.security import decode_jwt_token
from usrak.remote_address import get_remote_address

if TYPE_CHECKING:
    from usrak.core.config_schemas import AppConfig, RouterConfig

from usrak.core.managers.tokens.auth import AuthTokensManager


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
        request: Request,
        api_token: str,
        session: AsyncSession,
        app_config: "AppConfig",
        router_config: "RouterConfig",
        tokens_manager: AuthTokensManager,
):
    User = router_config.USER_MODEL

    payload = decode_jwt_token(api_token, app_config.JWT_API_TOKEN_SECRET_KEY)
    if not payload or not payload.user_identifier:
        return None
    if payload.token_type != enums.TokenTypes.API_TOKEN:
        return None

    result = await session.exec(select(User).where(User.user_identifier == payload.user_identifier))
    user = result.first()
    if not user:
        return None

    await tokens_manager.validate_api_token(
        token=api_token,
        session=session,
        user_identifier=payload.user_identifier,
        whitelisted_ip_addresses=(payload.secret_context.ip_addresses if payload.secret_context else None),
    )

    if payload.secret_context and payload.secret_context.ip_addresses:
        client_ip = get_remote_address(request)
        if client_ip not in payload.secret_context.ip_addresses:
            return None

    return user
