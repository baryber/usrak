
from typing import TYPE_CHECKING

from fastapi import Depends
from usrak.core.logger import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from usrak.core import enums
from usrak.core.models.user import UserModelBase
from usrak.core.schemas.user import UserCreate
from usrak.core.schemas.response import CommonDataNextStepResponse

from usrak.core.db import get_db
from usrak.core.dependencies.admin import get_admin
from usrak.core.dependencies.config_provider import get_router_config

from usrak.core.managers.sign_up.mail import MailSignupManager
from usrak.routes.signup import SignupUserData

if TYPE_CHECKING:
    from usrak.core.config_schemas import RouterConfig


AdminSignupResponse = CommonDataNextStepResponse[SignupUserData]


async def register_new_user(
    user_in: UserCreate,
    session: AsyncSession = Depends(get_db),
    admin: UserModelBase = Depends(get_admin),
    router_config: "RouterConfig" = Depends(get_router_config),
):
    """Register a new user on behalf of an admin."""

    signup_manager = MailSignupManager(session)
    user = await signup_manager.signup(
        email=user_in.email,
        plain_password=user_in.password,
        auth_provider="email",
        is_verified=True,
        is_active=True,
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

    data = SignupUserData(
        email=user.email,
        auth_provider=user.auth_provider,
        is_verified=user.is_verified,
        is_active=user.is_active,
        user_name=user.user_name,
    )

    return AdminSignupResponse(
        success=True,
        message="Operation completed",
        data=data,
        next_step=next_step,
    )
