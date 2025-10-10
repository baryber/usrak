from typing import TYPE_CHECKING

from fastapi import Depends
from fastapi.responses import Response

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from usrak.core import exceptions as exc
from usrak.core.schemas.user import UserLogin
from usrak.core.security import verify_password
from usrak.core.schemas.response import CommonResponse

from usrak.core.managers.tokens.auth import AuthTokensManager

from usrak.core.dependencies.config_provider import get_app_config, get_router_config

from usrak.core.db import get_db

if TYPE_CHECKING:
    from usrak.core.config_schemas import AppConfig, RouterConfig


async def login_user(
        response: Response,
        user_in: UserLogin,
        session: AsyncSession = Depends(get_db),
        app_config: "AppConfig" = Depends(get_app_config),
        router_config: "RouterConfig" = Depends(get_router_config),
        auth_tokens_manager: AuthTokensManager = Depends(AuthTokensManager)
):
    email = user_in.email.lower().strip()

    UserModel = router_config.USER_MODEL
    result = await session.exec(select(UserModel).where(UserModel.email == email))
    user = result.first()
    if not user:
        raise exc.InvalidCredentialsException

    if user_in.auth_provider != user.auth_provider:
        raise exc.AuthProviderMismatchException

    if not verify_password(user_in.password, user.hashed_password):
        raise exc.InvalidCredentialsException

    if not user.is_verified:
        raise exc.UserNotVerifiedException

    if not user.is_active:
        raise exc.UserDeactivatedException

    access_token = await auth_tokens_manager.create_access_token(
        user_identifier=user.user_identifier,
        password_version=user.password_version,
    )
    refresh_token = await auth_tokens_manager.create_refresh_token(
        user_identifier=user.user_identifier,
        password_version=user.password_version,
    )

    cookie_opts = {
        "httponly": True,
        "secure": app_config.COOKIE_SECURE,
        "samesite": app_config.COOKIE_SAMESITE,
    }

    response.set_cookie(
        key="access_token",
        value=access_token,
        **cookie_opts
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        **cookie_opts
    )

    return CommonResponse(
        success=True,
        message="Success login"
    )
