from typing import TYPE_CHECKING

from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import Depends

from usrak.core import enums
from usrak.core.schemas.user import UserCreate
from usrak.core.schemas.response import StatusResponse
from usrak.core.schemas.mail import EmailVerificationInput, EmailRequestCodeInput

from usrak.core.db import get_db
from usrak.core.managers.sign_up.mail import MailSignupManager

from usrak.core.dependencies.config_provider import get_router_config

if TYPE_CHECKING:
    from usrak.core.config_schemas import RouterConfig


async def signup(
        user_in: UserCreate,
        session: AsyncSession = Depends(get_db),
        router_config: "RouterConfig" = Depends(get_router_config),
        mail_signup_manager: MailSignupManager = Depends(MailSignupManager)
):

    user = await mail_signup_manager.signup(
        email=user_in.email,
        plain_password=user_in.password,
        auth_provider="email"
    )

    next_step = (enums.ResponseNextStep.VERIFY.value
                 if router_config.USE_VERIFICATION_LINKS_FOR_SIGNUP
                 else enums.ResponseNextStep.WAIT_FOR_VERIFICATION.value)

    # TODO: model_dump() from UserReadSchema
    data = {
        "email": user.email,
        "auth_provider": user.auth_provider,
        "is_verified": user.is_verified,
        "is_active": user.is_active
    }

    if user.user_name is not None:
        data["user_name"] = user.user_name

    return StatusResponse(
        success=True,
        message="Operation completed",
        data=data,
        next_step=next_step,
    )


async def send_signup_link(
        data: EmailRequestCodeInput,
        session: AsyncSession = Depends(get_db)
):
    signup_manager = MailSignupManager(session)

    await signup_manager.send_link(
        email=data.email,
        plain_password=data.plain_password,
    )

    return StatusResponse(
        success=True,
        message="Operation completed",
        next_step=enums.ResponseNextStep.VERIFY.value,
    )


async def verify_signup_link(
        data: EmailVerificationInput,
        session: AsyncSession = Depends(get_db)
):
    signup_manager = MailSignupManager(session)

    await signup_manager.verify(data.email, data.token)

    return StatusResponse(
        success=True,
        message="Operation completed",
        next_step=enums.ResponseNextStep.LOGIN.value,
    )
