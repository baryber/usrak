from typing import TYPE_CHECKING, Optional

from fastapi import Depends, Request, Security
from fastapi.security.api_key import APIKeyHeader
from sqlmodel.ext.asyncio.session import AsyncSession

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

api_token_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_access_token_from_cookies(request: Request) -> Optional[str]:
    return request.cookies.get("access_token")


def get_api_token_from_header(api_token: Optional[str] = Security(api_token_header)) -> Optional[str]:
    return api_token


def get_cached_user(request: Request):
    return getattr(request.state, "user", None)


def set_cached_user(request: Request, user):
    setattr(request.state, "user", user)


def build_optional_user_dep(mode: enums.AuthMode = enums.AuthMode.ANY):
    async def dep(
            request: Request,
            access_token: Optional[str] = Depends(get_access_token_from_cookies),
            api_token: Optional[str] = Depends(get_api_token_from_header),
            session: AsyncSession = Depends(get_db),
            app_config: "AppConfig" = Depends(get_app_config),
            router_config: "RouterConfig" = Depends(get_router_config),
            tokens_manager: AuthTokensManager = Depends(AuthTokensManager),
    ):
        cached = get_cached_user(request)
        if cached is not None:
            return cached

        try:
            if mode in (enums.AuthMode.ACCESS_ONLY, enums.AuthMode.ANY):
                if access_token:
                    user = await resolve_user_from_access_token(
                        access_token, session, app_config, router_config, tokens_manager
                    )
                    if user:
                        set_cached_user(request, user)
                        return user

            if mode in (enums.AuthMode.API_ONLY, enums.AuthMode.ANY):
                if api_token:
                    user = await resolve_user_from_api_token(
                        request, api_token, session, app_config, router_config, tokens_manager
                    )
                    if user:
                        set_cached_user(request, user)
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
