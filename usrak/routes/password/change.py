from sqlmodel import Session
from fastapi import Depends

from usrak.core.models.user import UserModelBase
from usrak.core import exceptions as exc, enums
from usrak.core.dependencies import user as user_deps
from usrak.core.schemas.response import StatusResponse

# from core.managers.password_reset import PasswordResetManager
from usrak.core.db import get_db


async def change_password(
        session: Session = Depends(get_db),
        user: UserModelBase = Depends(user_deps.get_user_if_verified_and_active)
):
    email = user.email
    if not email or user.auth_provider != "email":
        raise exc.UnauthorizedException

    # rm = PasswordResetManager(session=session)
    # await rm.send_link(email)

    return StatusResponse(
        success=True,
        message="Operation completed",
        next_step=enums.ResponseNextStep.VERIFY.value,
    )
