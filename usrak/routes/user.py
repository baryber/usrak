
from fastapi import Depends
from pydantic import BaseModel, EmailStr

from usrak.core.models.user import UserModelBase
from usrak.core.schemas.response import CommonDataResponse
from usrak.core.dependencies import user as user_deps


class UserProfileData(BaseModel):
    mail: EmailStr
    user_name: str | None = None
    user_id: str | None = None


UserProfileResponse = CommonDataResponse[UserProfileData]


def get_user(
    user: UserModelBase = Depends(user_deps.get_user_verified_and_active)
):
    data = UserProfileData(
        mail=user.email,
        user_name=user.user_name,
        user_id=user.external_id,
    )
    return UserProfileResponse(
        success=True,
        message="Operation completed",
        data=data,
    )


def user_profile(
    user: UserModelBase = Depends(user_deps.get_user_verified_and_active)
):
    data = UserProfileData(
        mail=user.email,
        user_name=user.user_name,
        user_id=user.external_id,
    )
    return UserProfileResponse(
        success=True,
        message="Operation completed",
        data=data,
    )
