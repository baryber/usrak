from typing import TYPE_CHECKING, Optional

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.requests import HTTPConnection

from usrak.core import exceptions as exc
from usrak.core.managers.tokens.auth import AuthTokensManager
from usrak.core.dependencies.config_provider import get_app_config, get_router_config
from usrak.core.db import get_db
from usrak.core import enums
from usrak.core.resolvers.user import (
    resolve_user_from_access_token,
    resolve_user_from_api_token,
)

if TYPE_CHECKING:
    from usrak.core.config_schemas import AppConfig, RouterConfig


def get_cached_user(connection: HTTPConnection):
    return getattr(connection.state, "user", None)


def set_cached_user(connection: HTTPConnection, user):
    setattr(connection.state, "user", user)


def build_optional_user_dep(mode: enums.AuthMode = enums.AuthMode.ANY):
    async def dep(
            connection: HTTPConnection,
            session: AsyncSession = Depends(get_db),
            app_config: "AppConfig" = Depends(get_app_config),
            router_config: "RouterConfig" = Depends(get_router_config),
            tokens_manager: AuthTokensManager = Depends(AuthTokensManager),
    ):
        cached = get_cached_user(connection)
        if cached is not None:
            return cached

        access_token: Optional[str] = connection.cookies.get("access_token")
        api_token: Optional[str] = connection.headers.get("X-API-Key")

        try:
            if mode in (enums.AuthMode.ACCESS_ONLY, enums.AuthMode.ANY):
                if access_token:
                    user = await resolve_user_from_access_token(
                        access_token, session, app_config, router_config, tokens_manager
                    )
                    if user:
                        set_cached_user(connection, user)
                        return user

            if mode in (enums.AuthMode.API_ONLY, enums.AuthMode.ANY):
                if api_token:
                    user = await resolve_user_from_api_token(
                        connection=connection,
                        api_token=api_token,
                        session=session,
                        router_config=router_config,
                        app_config=app_config,
                    )
                    if user:
                        set_cached_user(connection, user)
                        return user

        except (exc.UnauthorizedException, exc.InvalidTokenException):
            return None

        return None

    return dep


get_optional_user_any = build_optional_user_dep(enums.AuthMode.ANY)
get_optional_user_access_only = build_optional_user_dep(enums.AuthMode.ACCESS_ONLY)
get_optional_user_api_only = build_optional_user_dep(enums.AuthMode.API_ONLY)


async def get_user(user=Depends(get_optional_user_any)):
    if user is None:
        raise exc.UnauthorizedException()
    return user


async def get_user_access_only(user=Depends(get_optional_user_access_only)):
    if user is None:
        raise exc.UnauthorizedException()
    return user


async def get_user_api_only(user=Depends(get_optional_user_api_only)):
    if user is None:
        raise exc.UnauthorizedException()
    return user


async def get_user_verified_and_active(user=Depends(get_user)):
    if not user.is_verified:
        raise exc.UserNotVerifiedException()
    if not user.is_active:
        raise exc.UserDeactivatedException()
    return user
