from fastapi import Depends

from usrak.core.models.user import UserModelBase
from usrak.core.schemas.response import StatusResponse
from usrak.core.dependencies import user as user_deps


async def get_user(
    user: UserModelBase = Depends(user_deps.get_user_if_verified_and_active)
):
    return StatusResponse(
        status=True,
        message="Operation completed",
        data={
            "mail": user.email,
            "user_name": user.user_name,
            "user_id": user.external_id,
        },
    )


async def user_profile(
    user: UserModelBase = Depends(user_deps.get_user_if_verified_and_active)
):

    return StatusResponse(
        status=True,
        message="Operation completed",
        data={
            "mail": user.email,
            "user_name": user.user_name,
            "user_id": user.external_id,
        },
    )


