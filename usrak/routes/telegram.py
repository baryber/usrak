import hmac
import hashlib
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pydantic import BaseModel
from fastapi import Depends
from sqlmodel import select, Session
from starlette.responses import RedirectResponse

from usrak.core import exceptions as exc
from usrak.utils.internal_id import generate_internal_id_from_str as gen_internal_id

from usrak.core.managers.tokens.auth import AuthTokensManager

from usrak.core.dependencies.managers import get_user_model
from usrak.core.dependencies.config_provider import get_app_config

from usrak.core.db import get_db

if TYPE_CHECKING:
    from usrak.core.config_schemas import AppConfig


class TelegramUser(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


def check_telegram_auth(data: dict[str, str], bot_token: str) -> bool:
    check_hash = data.pop("hash")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    hmac_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(hmac_hash.encode(), check_hash.encode())


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


async def telegram_auth(
        user: TelegramUser,
        session: Session = Depends(get_db),
        app_config: "AppConfig" = Depends(get_app_config),
        auth_tokens_manager: AuthTokensManager = Depends(AuthTokensManager)
):
    current_time = datetime.now(timezone.utc).timestamp()
    if current_time - user.auth_date > 300:
        raise exc.InvalidTelegramAuthException(extra_detail="Authorization data is too old")

    data = user.dict()
    if not check_telegram_auth(data, app_config.TELEGRAM_AUTH_BOT_TOKEN):
        raise exc.InvalidTelegramAuthException

    User = get_user_model()
    user = session.exec(select(User).where(User.external_id == user.id)).first()
    if not user:
        user = User(
            auth_provider="telegram",
            external_id=str(user.id),
            internal_id=gen_internal_id(),
            user_name=user.username or user.username or f"{user.first_name} {user.last_name or ''}".strip(),
            is_active=True,
            is_verified=True,
            signed_up_at=datetime.now(timezone.utc),
            hashed_password=None,
        )
        session.add(user)
        session.commit()

    else:
        if user.auth_provider != "telegram":
            raise exc.AuthProviderMismatchException

    if not user.is_active:
        raise exc.UserDeactivatedException

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
