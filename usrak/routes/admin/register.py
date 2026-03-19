from typing import TYPE_CHECKING
from typing import get_args

from fastapi import Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm.attributes import set_attribute
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from usrak.core.logger import logger

from usrak.core import enums
from usrak.core import exceptions as exc
from usrak.core.dependencies.managers import get_user_model
from usrak.core.models.user import UserModelBase
from usrak.core.policies.user_management import UserManagementPolicy
from usrak.core.roles import get_user_role
from usrak.core.schemas.response import CommonDataNextStepResponse, CommonDataResponse, CommonResponse
from usrak.core.schemas.user import AdminUserCreate, AdminUserUpdate
from usrak.core.security import hash_password

from usrak.core.db import get_db
from usrak.core.dependencies.role import require_roles
from usrak.core.dependencies.config_provider import get_router_config
from usrak.core.enums import UserManagementAction

from usrak.core.managers.sign_up.mail import MailSignupManager

if TYPE_CHECKING:
    from usrak.core.config_schemas import RouterConfig


class ManagedUserData(BaseModel):
    user_identifier: str | int | None = None
    email: EmailStr
    auth_provider: str
    is_verified: bool
    is_active: bool
    user_name: str | None = None
    external_id: str | None = None
    role: str | None = None


AdminSignupResponse = CommonDataNextStepResponse[ManagedUserData]
AdminUserResponse = CommonDataResponse[ManagedUserData]


def _build_user_data(user: UserModelBase, role: str | None = None) -> ManagedUserData:
    return ManagedUserData(
        user_identifier=getattr(user, "user_identifier", None),
        email=user.email,
        auth_provider=getattr(user, "auth_provider", "email"),
        is_verified=user.is_verified,
        is_active=user.is_active,
        user_name=getattr(user, "user_name", None),
        external_id=getattr(user, "external_id", None),
        role=getattr(user, "role", role),
    )


def _coerce_user_identifier(raw_identifier: str):
    user_model = get_user_model()
    identifier_field_name = getattr(user_model, "__id_field_name__", "id")
    field_info = user_model.model_fields.get(identifier_field_name)
    if field_info is None:
        return raw_identifier

    annotation = field_info.annotation
    candidate_types = [candidate for candidate in get_args(annotation) if candidate is not type(None)]
    if not candidate_types:
        candidate_types = [annotation]

    for candidate_type in candidate_types:
        if isinstance(candidate_type, type):
            try:
                return candidate_type(raw_identifier)
            except (TypeError, ValueError):
                continue

    return raw_identifier


def _set_user_field(user: UserModelBase, field_name: str, value) -> None:
    set_attribute(user, field_name, value)


async def _get_target_user(session: AsyncSession, raw_identifier: str) -> UserModelBase:
    user_model = get_user_model()
    identifier = _coerce_user_identifier(raw_identifier)
    result = await session.exec(select(user_model).where(user_model.user_identifier == identifier))
    user = result.first()
    if user is None:
        raise exc.UserNotFoundException()
    return user


async def register_new_user(
    user_in: AdminUserCreate,
    session: AsyncSession = Depends(get_db),
    admin: UserModelBase = Depends(require_roles("*")),
    router_config: "RouterConfig" = Depends(get_router_config),
    signup_manager: MailSignupManager = Depends(MailSignupManager),
    policy: UserManagementPolicy = Depends(UserManagementPolicy),
):
    """Register a new user on behalf of an admin."""

    target_role = user_in.role or str(router_config.DEFAULT_ROLES_ENUM.USER.value)
    await policy.authorize(
        action=UserManagementAction.CREATE,
        actor_role=get_user_role(admin),
        target_current_role=None,
        target_new_role=target_role,
    )

    user = await signup_manager.signup(
        email=user_in.email,
        plain_password=user_in.password,
        auth_provider="email",
        is_verified=True,
        is_active=True,
        role=target_role,
        user_name=user_in.user_name,
        external_id=user_in.external_id,
    )
    logger.info(
        "User %s registered by admin %s with ID %s.",
        user.email,
        admin.email,
        admin.user_identifier,
    )

    next_step = (
        enums.ResponseNextStep.VERIFY.value
        if router_config.USE_VERIFICATION_LINKS_FOR_SIGNUP
        else enums.ResponseNextStep.LOGIN.value
    )

    return AdminSignupResponse(
        success=True,
        message="Operation completed",
        data=_build_user_data(user, role=target_role),
        next_step=next_step,
    )


async def update_user(
    user_identifier: str,
    user_in: AdminUserUpdate,
    session: AsyncSession = Depends(get_db),
    admin: UserModelBase = Depends(require_roles("*")),
    policy: UserManagementPolicy = Depends(UserManagementPolicy),
):
    target_user = await _get_target_user(session, user_identifier)
    requested_role = user_in.role if "role" in user_in.model_fields_set else None

    await policy.authorize(
        action=UserManagementAction.UPDATE,
        actor_role=get_user_role(admin),
        target_current_role=get_user_role(target_user),
        target_new_role=requested_role,
    )

    if "email" in user_in.model_fields_set:
        _set_user_field(target_user, "email", user_in.email)
    if "password" in user_in.model_fields_set:
        _set_user_field(target_user, "hashed_password", hash_password(user_in.password))
        _set_user_field(target_user, "password_version", (target_user.password_version or 0) + 1)
    if "external_id" in user_in.model_fields_set:
        _set_user_field(target_user, "external_id", user_in.external_id)
    if "user_name" in user_in.model_fields_set:
        _set_user_field(target_user, "user_name", user_in.user_name)
    if "role" in user_in.model_fields_set:
        _set_user_field(target_user, "role", user_in.role)
    if "is_active" in user_in.model_fields_set:
        _set_user_field(target_user, "is_active", user_in.is_active)
    if "is_verified" in user_in.model_fields_set:
        _set_user_field(target_user, "is_verified", user_in.is_verified)

    session.add(target_user)
    await session.commit()
    await session.refresh(target_user)

    logger.info(
        "User %s updated by admin %s with ID %s.",
        target_user.email,
        admin.email,
        admin.user_identifier,
    )

    return AdminUserResponse(
        success=True,
        message="Operation completed",
        data=_build_user_data(target_user),
    )


async def delete_user(
    user_identifier: str,
    session: AsyncSession = Depends(get_db),
    admin: UserModelBase = Depends(require_roles("*")),
    policy: UserManagementPolicy = Depends(UserManagementPolicy),
):
    target_user = await _get_target_user(session, user_identifier)

    await policy.authorize(
        action=UserManagementAction.DELETE,
        actor_role=get_user_role(admin),
        target_current_role=get_user_role(target_user),
        target_new_role=None,
    )

    _set_user_field(target_user, "is_active", False)
    session.add(target_user)
    await session.commit()

    logger.info(
        "User %s deactivated by admin %s with ID %s.",
        target_user.email,
        admin.email,
        admin.user_identifier,
    )

    return CommonResponse(
        success=True,
        message="Operation completed",
    )
