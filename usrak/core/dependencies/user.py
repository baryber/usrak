from typing import TYPE_CHECKING, Optional

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


async def get_optional_user(
    request: Request,
    session: Session = Depends(get_db),
    app_config: "AppConfig" = Depends(get_app_config),
    router_config: "RouterConfig" = Depends(get_router_config),
    auth_tokens_manager: AuthTokensManager = Depends(AuthTokensManager),
) -> Optional[UserModelBase]:
    """
    Fetches the authenticated user based on the access token from the request cookies.
    If authentication fails for any reason (e.g., missing token, invalid token),
    it returns None instead of raising an exception.

    This is useful for endpoints that can be accessed by both authenticated and
    anonymous users, or for middleware that needs to identify a user without
    blocking the request.
    """
    try:
        User = router_config.USER_MODEL

        access_token = request.cookies.get("access_token")
        if not access_token:
            return None

        payload = decode_jwt_token(
            token=access_token,
            jwt_secret=app_config.JWT_ACCESS_TOKEN_SECRET_KEY,
        )
        if not (payload and payload.user_identifier):
            return None

        user = session.exec(select(User).where(User.user_identifier == payload.user_identifier)).first()
        if not user:
            return None

        await auth_tokens_manager.validate_access_token(
            token=access_token,
            user_identifier=payload.user_identifier,
            password_version=user.password_version,
        )

        return user

    except Exception:
        # TODO: Feature: catch authentication-related exceptions

        return None


async def get_user(
    user: Optional[UserModelBase] = Depends(get_optional_user),
) -> UserModelBase:
    """
    Requires an authenticated user.

    This dependency relies on `get_optional_user`. If `get_optional_user`
    returns None (meaning the user is not authenticated), this function
    raises an `UnauthorizedException`.

    This should be used for endpoints that are protected and require a valid login.
    """
    if user is None:
        raise exc.UnauthorizedException()
    return user


async def get_user_if_verified_and_active(
    user: UserModelBase = Depends(get_user),
) -> UserModelBase:
    """
    Requires an authenticated user who is also verified and active.

    This dependency relies on `get_user`, which ensures the user is authenticated.
    It then performs additional checks for the `is_verified` and `is_active` flags.
    """
    if not user.is_verified:
        raise exc.UserNotVerifiedException()

    if not user.is_active:
        raise exc.UserDeactivatedException()

    return user