from fastapi import Depends

from usrak.core.logger import logger

from usrak.core.models.user import UserModelBase
from usrak.core.schemas.response import StatusResponse
from usrak.core.dependencies import user as user_deps


async def check_auth(
    user: UserModelBase = Depends(user_deps.get_user_if_verified_and_active)
):
    logger.info(f"User {user.internal_id} is authenticated by check_auth endpoint")
    return StatusResponse(
        success=True,
        message="Operation completed",
        data={
            "is_authenticated": True,
        },
    )
