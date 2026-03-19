from typing import Optional

from fastapi import Response, Request, Depends

from usrak.core.models.user import UserModelBase
from usrak.core.schemas.response import CommonResponse

from usrak.core.managers.tokens.auth import AuthTokensManager

from usrak.core.dependencies import user as user_deps


get_user_optional = user_deps.build_user_dependency(
    optional=True,
    require_verified=True,
    require_active=True,
)
setattr(get_user_optional, "__name__", "get_user_optional")

async def logout_user(
        response: Response,
        request: Request,
        user: Optional[UserModelBase] = Depends(get_user_optional),
        auth_tokens_manager: AuthTokensManager = Depends(AuthTokensManager)
):
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")

    if access_token and refresh_token and user:
        await auth_tokens_manager.terminate_all_user_sessions(user_identifier=user.user_identifier)

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return CommonResponse(
        success=True,
        message="Operation completed",
    )
