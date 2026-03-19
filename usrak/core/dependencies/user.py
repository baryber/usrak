from collections.abc import Awaitable, Callable, Sequence
from enum import Enum
from typing import TYPE_CHECKING, Literal, TypeAlias, overload

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.requests import HTTPConnection

from usrak.core import enums
from usrak.core import exceptions as exc
from usrak.core.dependencies.config_provider import get_app_config, get_router_config
from usrak.core.db import get_db
from usrak.core.managers.tokens.auth import AuthTokensManager
from usrak.core.models.role import RoleModelBase
from usrak.core.resolvers.user import (
    resolve_user_from_access_token,
    resolve_user_from_api_token,
)
from usrak.core.roles import get_user_role, normalize_role_reference

if TYPE_CHECKING:
    from usrak.core.config_schemas import AppConfig, RouterConfig
    from usrak.core.models.user import UserModelBase


RoleRequirement: TypeAlias = RoleModelBase | Enum | str | Literal["*"]
UserDependency: TypeAlias = Callable[..., Awaitable["UserModelBase"]]
OptionalUserDependency: TypeAlias = Callable[..., Awaitable["UserModelBase | None"]]
AuthSource: TypeAlias = Literal["access", "api"]

_USER_CACHE_ATTR = "_usrak_user_cache"
_OPTIONAL_DEPENDENCY_EXCEPTIONS = (
    exc.AccessDeniedException,
    exc.ExpiredAccessTokenException,
    exc.InvalidAccessTokenException,
    exc.InvalidCredentialsException,
    exc.InvalidRefreshTokenException,
    exc.InvalidTokenException,
    exc.UnauthorizedException,
    exc.UserDeactivatedException,
    exc.UserNotVerifiedException,
)


def _get_user_cache(connection: HTTPConnection) -> dict[str, "UserModelBase"]:
    cache = getattr(connection.state, _USER_CACHE_ATTR, None)
    if cache is None:
        cache = {}
        setattr(connection.state, _USER_CACHE_ATTR, cache)
    return cache


def get_cached_user(connection: HTTPConnection, source: AuthSource) -> "UserModelBase | None":
    return _get_user_cache(connection).get(source)


def set_cached_user(connection: HTTPConnection, source: AuthSource, user: "UserModelBase") -> None:
    _get_user_cache(connection)[source] = user


def _iter_auth_sources(mode: enums.AuthMode) -> tuple[AuthSource, ...]:
    if mode == enums.AuthMode.ACCESS_ONLY:
        return ("access",)
    if mode == enums.AuthMode.API_ONLY:
        return ("api",)
    return ("access", "api")


def _normalize_required_roles(
    require_roles: Sequence[RoleRequirement] | None,
    router_config: "RouterConfig",
) -> set[str] | None:
    if not require_roles:
        return None

    normalized_roles = {
        normalize_role_reference(role, router_config)
        for role in require_roles
    }
    if "*" in normalized_roles:
        return None
    return normalized_roles


def _apply_user_filters(
    user: "UserModelBase",
    *,
    require_verified: bool,
    require_active: bool,
    require_roles: Sequence[RoleRequirement] | None,
    router_config: "RouterConfig",
) -> "UserModelBase":
    if require_verified and not user.is_verified:
        raise exc.UserNotVerifiedException()
    if require_active and not user.is_active:
        raise exc.UserDeactivatedException()

    normalized_roles = _normalize_required_roles(require_roles, router_config)
    if normalized_roles is None:
        return user

    if get_user_role(user) not in normalized_roles:
        raise exc.AccessDeniedException()
    return user


async def _resolve_user_from_source(
    *,
    source: AuthSource,
    connection: HTTPConnection,
    session: AsyncSession,
    app_config: "AppConfig",
    router_config: "RouterConfig",
    tokens_manager: AuthTokensManager,
) -> "UserModelBase | None":
    if source == "access":
        access_token = connection.cookies.get("access_token")
        if not access_token:
            return None
        return await resolve_user_from_access_token(
            access_token=access_token,
            session=session,
            app_config=app_config,
            router_config=router_config,
            tokens_manager=tokens_manager,
        )

    api_token = connection.headers.get("X-API-Key")
    if not api_token:
        return None
    return await resolve_user_from_api_token(
        connection=connection,
        api_token=api_token,
        session=session,
        router_config=router_config,
        app_config=app_config,
    )


async def _resolve_user(
    *,
    connection: HTTPConnection,
    session: AsyncSession,
    app_config: "AppConfig",
    router_config: "RouterConfig",
    tokens_manager: AuthTokensManager,
    auth_mode: enums.AuthMode,
) -> "UserModelBase | None":
    for source in _iter_auth_sources(auth_mode):
        cached_user = get_cached_user(connection, source)
        if cached_user is not None:
            return cached_user

        user = await _resolve_user_from_source(
            source=source,
            connection=connection,
            session=session,
            app_config=app_config,
            router_config=router_config,
            tokens_manager=tokens_manager,
        )
        if user is not None:
            set_cached_user(connection, source, user)
            return user

    return None


@overload
def build_user_dependency(
    *,
    auth_mode: enums.AuthMode = enums.AuthMode.ANY,
    require_verified: bool = False,
    require_active: bool = False,
    require_roles: Sequence[RoleRequirement] | None = None,
    optional: Literal[False] = False,
) -> UserDependency: ...


@overload
def build_user_dependency(
    *,
    auth_mode: enums.AuthMode = enums.AuthMode.ANY,
    require_verified: bool = False,
    require_active: bool = False,
    require_roles: Sequence[RoleRequirement] | None = None,
    optional: Literal[True],
) -> OptionalUserDependency: ...


def build_user_dependency(
    *,
    auth_mode: enums.AuthMode = enums.AuthMode.ANY,
    require_verified: bool = False,
    require_active: bool = False,
    require_roles: Sequence[RoleRequirement] | None = None,
    optional: bool = False,
) -> UserDependency | OptionalUserDependency:
    async def dep(
        connection: HTTPConnection,
        session: AsyncSession = Depends(get_db),
        app_config: "AppConfig" = Depends(get_app_config),
        router_config: "RouterConfig" = Depends(get_router_config),
        tokens_manager: AuthTokensManager = Depends(AuthTokensManager),
    ) -> "UserModelBase | None":
        try:
            user = await _resolve_user(
                connection=connection,
                session=session,
                app_config=app_config,
                router_config=router_config,
                tokens_manager=tokens_manager,
                auth_mode=auth_mode,
            )
            if user is None:
                raise exc.UnauthorizedException()

            return _apply_user_filters(
                user,
                require_verified=require_verified,
                require_active=require_active,
                require_roles=require_roles,
                router_config=router_config,
            )
        except _OPTIONAL_DEPENDENCY_EXCEPTIONS:
            if optional:
                return None
            raise

    return dep


def build_optional_user_dep(mode: enums.AuthMode = enums.AuthMode.ANY) -> OptionalUserDependency:
    return build_user_dependency(auth_mode=mode, optional=True)


get_optional_user_any = build_user_dependency(
    auth_mode=enums.AuthMode.ANY,
    optional=True,
)
setattr(get_optional_user_any, "__name__", "get_optional_user_any")

get_optional_user_access_only = build_user_dependency(
    auth_mode=enums.AuthMode.ACCESS_ONLY,
    optional=True,
)
setattr(get_optional_user_access_only, "__name__", "get_optional_user_access_only")

get_optional_user_api_only = build_user_dependency(
    auth_mode=enums.AuthMode.API_ONLY,
    optional=True,
)
setattr(get_optional_user_api_only, "__name__", "get_optional_user_api_only")

get_user = build_user_dependency()
setattr(get_user, "__name__", "get_user")

get_user_access_only = build_user_dependency(
    auth_mode=enums.AuthMode.ACCESS_ONLY,
)
setattr(get_user_access_only, "__name__", "get_user_access_only")

get_user_api_only = build_user_dependency(
    auth_mode=enums.AuthMode.API_ONLY,
)
setattr(get_user_api_only, "__name__", "get_user_api_only")

get_user_verified_and_active = build_user_dependency(
    require_verified=True,
    require_active=True,
)
setattr(get_user_verified_and_active, "__name__", "get_user_verified_and_active")
