from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from usrak.core.schemas.response import CommonResponse
from usrak.core.schemas.password import ForgotPasswordRequestInput

from usrak.core.db import get_db
# from core.managers.password_reset import PasswordResetManager


async def forgot_password(
        data: ForgotPasswordRequestInput,
        session: AsyncSession = Depends(get_db),
):
    # rm = PasswordResetManager(session=session)
    # await rm.send_link(data.email)

    return CommonResponse(
        success=True,
        message="Operation completed",
    )
