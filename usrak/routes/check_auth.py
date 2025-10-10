from fastapi import Depends
from pydantic import BaseModel

from usrak.core.logger import logger

from usrak.core.models.user import UserModelBase
from usrak.core.schemas.response import CommonDataResponse
from usrak.core.dependencies import user as user_deps


class AuthenticatedData(BaseModel):
    is_authenticated: bool = True


async def check_auth(
    user: UserModelBase = Depends(user_deps.get_user_verified_and_active)
):
    logger.info(f"User {user.user_identifier} is authenticated by check_auth endpoint")
    return CommonDataResponse(
        success=True,
        message="Operation completed",
        data=AuthenticatedData(is_authenticated=True),
    )
