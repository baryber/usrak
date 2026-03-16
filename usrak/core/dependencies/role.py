from enum import Enum
from typing import TYPE_CHECKING, Literal

from sqlmodel import select
from fastapi import Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from usrak.core import exceptions as exc
from usrak.core.security import decode_jwt_token
from usrak.core.models.role import RoleModelBase
from usrak.core.models.user import UserModelBase
from usrak.core.managers.tokens.auth import AuthTokensManager

from usrak.core.dependencies.managers import get_user_model
from usrak.core.dependencies.config_provider import get_app_config, get_router_config

from usrak.core.db import get_db

if TYPE_CHECKING:
    from usrak.core.config_schemas import AppConfig, RouterConfig


def _normalize_required_role(
    role: RoleModelBase | str | Literal["*"],
    router_config: "RouterConfig",
) -> str:
    if role == "*":
        return role

    if isinstance(role, RoleModelBase):
        return role.name

    if isinstance(role, Enum):
        configured_roles = router_config.DEFAULT_ROLES_ENUM
        if role.name in configured_roles.__members__:
            return str(configured_roles[role.name].value)
        return str(role.value)

    return str(role)


def require_roles(roles: RoleModelBase | str | Literal["*"]):
    async def dep(
        request: Request,
        session: AsyncSession = Depends(get_db),
        app_config: "AppConfig" = Depends(get_app_config),
        router_config: "RouterConfig" = Depends(get_router_config),
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
        result = await session.exec(select(User).where(User.user_identifier == jwt_payload.user_identifier))
        user = result.first()
        if not user:
            raise exc.InvalidCredentialsException

        required_role = _normalize_required_role(roles, router_config)
        if required_role != "*":
            role_field_name = getattr(user, "__role_field_name__", "role")
            user_role = getattr(user, role_field_name, None)
            if user_role != required_role:
                raise exc.AccessDeniedException

        await auth_tokens_manager.validate_access_token(
            token=access_token,
            user_identifier=jwt_payload.user_identifier,
            password_version=user.password_version,
        )

        return user

    return dep
