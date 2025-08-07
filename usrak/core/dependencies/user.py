from typing import TYPE_CHECKING

from sqlmodel import select, Session
from fastapi import Depends, Request

from usrak.core import exceptions as exc
from usrak.core.models import UserModelBase
from usrak.core.security import decode_jwt_token
from usrak.core.managers.tokens.auth import AuthTokensManager

from usrak.core.dependencies.config_provider import get_app_config, get_router_config

from usrak.core.db import get_db

if TYPE_CHECKING:
    from usrak.core.config_schemas import AppConfig, RouterConfig


async def get_user(
        request: Request,
        session: Session = Depends(get_db),
        app_config: "AppConfig" = Depends(get_app_config),
        router_config: "RouterConfig" = Depends(get_router_config),
        auth_tokens_manager: AuthTokensManager = Depends(AuthTokensManager),
) -> UserModelBase:
    """Fetches the authenticated user based on the access token from the request cookies."""

    User = router_config.USER_MODEL

    access_token = request.cookies.get("access_token")
    if not access_token:
        raise exc.UnauthorizedException

    payload = decode_jwt_token(
        token=access_token,
        jwt_secret=app_config.JWT_ACCESS_TOKEN_SECRET_KEY,
    )
    if payload is None:
        raise exc.InvalidAccessTokenException

    if payload.user_identifier is None:
        raise exc.InvalidAccessTokenException

    user = session.exec(select(User).where(User.user_identifier == payload.user_identifier)).first()
    if not user:
        raise exc.InvalidCredentialsException

    await auth_tokens_manager.validate_access_token(
        token=access_token,
        user_identifier=payload.user_identifier,
        password_version=user.password_version,
    )

    return user


async def get_user_if_verified_and_active(
        user: UserModelBase = Depends(get_user),
):
    if not user.is_verified:
        raise exc.UserNotVerifiedException

    if not user.is_active:
        raise exc.UserDeactivatedException

    return user
