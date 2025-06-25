from sqlmodel import Session
from fastapi import Depends, Response

from usrak.core.schemas.response import StatusResponse
from usrak.core.schemas.password import PasswordResetVerificationInput, VerifyResetPasswordTokenInput

from usrak.core.db import get_db
# from core.logic import PasswordResetManager


async def verify_token(
        data: VerifyResetPasswordTokenInput,
        session: Session = Depends(get_db),
):
    # rm = PasswordResetManager(session=session)
    # await rm.verify_token(email=data.email, reset_token=data.token)
    return StatusResponse(
        success=True,
        message="Operation completed",
    )


async def reset_password(
        response: Response,
        data: PasswordResetVerificationInput,
        session: Session = Depends(get_db),
):
    # rm = PasswordResetManager(session=session)
    # await rm.reset(
    #     reset_token=data.token,
    #     new_password=data.new_password,
    #     email=data.email
    # )
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")

    return StatusResponse(
        success=True,
        message="Operation completed",
    )
