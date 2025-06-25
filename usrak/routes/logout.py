from typing import Optional

from sqlmodel import Session
from fastapi import Response, Request, Depends

from usrak.core import exceptions as exc
from usrak.core.models.user import UserModelBase
from usrak.core.schemas.response import StatusResponse

from usrak.core.managers.tokens.auth import AuthTokensManager

from usrak.core.dependencies import user as user_deps


async def get_user_optional(
        user: UserModelBase = Depends(user_deps.get_user),
) -> Optional[UserModelBase]:
    try:

        if not user.is_verified or not user.is_active:
            return None

        return user

    except (
            exc.UnauthorizedException,
            exc.InvalidAccessTokenException,
            exc.InvalidRefreshTokenException,
    ):
        return None


async def logout_user(
        response: Response,
        request: Request,
        user: Optional[UserModelBase] = Depends(get_user_optional),
        auth_tokens_manager: AuthTokensManager = Depends(AuthTokensManager)
):
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")

    if access_token and refresh_token and user:
        await auth_tokens_manager.terminate_all_user_sessions(user_identifier=user.internal_id)

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return StatusResponse(
        success=True,
        message="Operation completed",
    )
