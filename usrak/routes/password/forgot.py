from sqlmodel import Session
from fastapi import Depends

from usrak.core.schemas.response import StatusResponse
from usrak.core.schemas.password import ForgotPasswordRequestInput

from usrak.core.db import get_db
# from core.managers.password_reset import PasswordResetManager


async def forgot_password(
        data: ForgotPasswordRequestInput,
        session: Session = Depends(get_db),
):
    # rm = PasswordResetManager(session=session)
    # await rm.send_link(data.email)

    return StatusResponse(
        success=True,
        message="Operation completed",
    )
