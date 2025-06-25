from uuid import uuid4
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlmodel import select, Session
from starlette.responses import RedirectResponse
from fastapi import Depends, Request

from usrak.core import exceptions as exc
from usrak.core.google import exchange_code_for_token, get_userinfo
from usrak.utils.internal_id import generate_internal_id_from_str as gen_internal_id

from usrak.core.managers.tokens.auth import AuthTokensManager

from usrak.core.dependencies.managers import get_user_model
from usrak.core.dependencies.config_provider import get_app_config

from usrak.core.db import get_db

if TYPE_CHECKING:
    from usrak.core.config_schemas import AppConfig


def set_auth_cookies(
        response: RedirectResponse,
        app_config: "AppConfig",
        access_token: str,
        refresh_token: str
):
    cookie_options = {
        "httponly": True,
        "secure": app_config.COOKIE_SECURE,
        "samesite": app_config.COOKIE_SAMESITE,
    }
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=app_config.ACCESS_TOKEN_EXPIRE_SEC,
        **cookie_options
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=app_config.REFRESH_TOKEN_EXPIRE_SEC,
        **cookie_options
    )


def google_oauth(
        app_config: "AppConfig" = Depends(get_app_config),
):
    state = str(uuid4())
    params = {
        "client_id": app_config.GOOGLE_CLIENT_ID,
        "redirect_uri": app_config.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "email profile",
        "state": state,
    }

    query = "&".join([f"{k}={v}" for k, v in params.items()])
    url = f"{app_config.GOOGLE_AUTH_URL}?{query}"

    response = RedirectResponse(url)
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=True
    )
    return response


async def google_oauth_callback(
        request: Request,
        session: Session = Depends(get_db),
        app_config: "AppConfig" = Depends(get_app_config),
        auth_tokens_manager: AuthTokensManager = Depends(AuthTokensManager),
):
    code = request.query_params.get("code")
    if not code:
        raise exc.NoCodeProvidedGoogleOauthException

    state = request.query_params.get("state")
    stored_state = request.cookies.get("oauth_state")
    if not state or state != stored_state:
        raise exc.StateMismatchGoogleOauthException

    token_data = await exchange_code_for_token(code)
    if not token_data:
        raise exc.CodeExchangeErrorGoogleOauthException

    userinfo = await get_userinfo(token_data["access_token"])
    if not userinfo or "email" not in userinfo:
        raise exc.NoUserinfoReceivedGoogleOauthException

    google_mail = userinfo["email"]

    User = get_user_model()
    user = session.exec(select(User).where(User.email == google_mail)).first()
    if not user:
        user = User(
            auth_provider="google",
            email=google_mail,
            internal_id=gen_internal_id(),
            external_id=userinfo.get("sub"),
            is_active=True,
            is_verified=True,
            hashed_password=None,
            signed_up_at=datetime.now(timezone.utc),
        )
        session.add(user)
        session.commit()

    if not user.is_active:
        raise exc.UserDeactivatedException

    if user.auth_provider != "google":
        raise exc.InvalidCredentialsException

    access_token = await auth_tokens_manager.create_access_token(
        user_identifier=user.internal_id,
        password_version=user.password_version,
    )
    refresh_token = await auth_tokens_manager.create_refresh_token(
        user_identifier=user.internal_id,
        password_version=user.password_version,
    )

    response = RedirectResponse(url=app_config.REDIRECT_AFTER_AUTH_URL)
    set_auth_cookies(
        response=response,
        app_config=app_config,
        access_token=access_token,
        refresh_token=refresh_token
    )

    return response
