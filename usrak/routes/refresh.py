from fastapi import Depends, Response, Request

from usrak.core import exceptions as exc
from usrak.core.models.user import UserModelBase
from usrak.core.schemas.response import StatusResponse

from usrak.core.managers.tokens.auth import AuthTokensManager

from usrak.core.dependencies import user as user_deps
from usrak.core.dependencies.config_provider import get_app_config


def set_auth_cookies(response: Response, access_token: str, refresh_token: str = None):
    app_config = get_app_config()

    cookie_options = {
        "httponly": True,
        "secure": app_config.COOKIE_SECURE,
        "samesite": app_config.COOKIE_SAMESITE,
    }
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=app_config.ACCESS_TOKEN_EXPIRE_SEC,
        **cookie_options
    )
    if refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=app_config.REFRESH_TOKEN_EXPIRE_SEC,
            **cookie_options
        )


async def refresh_token(
        request: Request,
        response: Response,
        user: UserModelBase = Depends(user_deps.get_user_if_verified_and_active),
        auth_tokens_manager: AuthTokensManager = Depends(AuthTokensManager),
):
    rf_token = request.cookies.get("refresh_token")
    access_token = request.cookies.get("access_token")
    if not refresh_token or not access_token:
        raise exc.UnauthorizedException

    new_refresh_token = await auth_tokens_manager.handle_refresh_token(
        refresh_token=rf_token,
        user_identifier=user.internal_id,
        password_version=user.password_version,
        old_access_token=access_token,
    )

    new_access_token = await auth_tokens_manager.create_access_token(
        user_identifier=user.internal_id,
        password_version=user.password_version,
    )

    set_auth_cookies(response, new_access_token, new_refresh_token)

    return StatusResponse(
        success=True,
        message="Operation completed",
    )
