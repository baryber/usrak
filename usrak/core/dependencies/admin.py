from typing import TYPE_CHECKING

from sqlmodel import select, Session
from fastapi import Depends, Request

from usrak.core import exceptions as exc
from usrak.core.security import decode_jwt_token
from usrak.core.models.user import UserModelBase
from usrak.core.managers.tokens.auth import AuthTokensManager

from usrak.core.dependencies.managers import get_user_model
from usrak.core.dependencies.config_provider import get_router_config
from usrak.core.dependencies.config_provider import get_app_config

from usrak.core.db import get_db

if TYPE_CHECKING:
    from usrak.core.config_schemas import AppConfig, RouterConfig


async def get_admin(
        request: Request,
        session: Session = Depends(get_db),
        app_config: "AppConfig" = Depends(get_app_config),
        auth_tokens_manager: AuthTokensManager = Depends(AuthTokensManager),
) -> UserModelBase:
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise exc.UnauthorizedException

    jwt_payload = decode_jwt_token(
        token=access_token,
        jwt_secret=app_config.JWT_ACCESS_TOKEN_SECRET_KEY,
    )
    if jwt_payload is None:
        raise exc.InvalidAccessTokenException

    if jwt_payload.user_identifier is None:
        raise exc.InvalidAccessTokenException

    User = get_user_model()
    user = session.exec(select(User).where(User.user_identifier == jwt_payload.user_identifier)).first()
    if not user:
        raise exc.InvalidCredentialsException

    if not user.is_admin:
        raise exc.AccessDeniedException

    await auth_tokens_manager.validate_access_token(
        token=access_token,
        user_identifier=jwt_payload.user_identifier,
        password_version=user.password_version,
    )

    return user
