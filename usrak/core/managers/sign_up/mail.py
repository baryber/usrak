from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import Depends

from sqlmodel import Session, select

from usrak.core import exceptions as exc, dependencies as deps
from usrak.core.models.user import UserModelBase
from usrak.core.security import verify_password, hash_password

from usrak.utils.identifier import generate_identifier_from_str as gen_internal_id
from usrak.core.managers.tokens.one_time import OneTimeTokensManager

from usrak.core.db import get_db
from usrak.core.dependencies.managers import get_user_model, get_user_read_schema
from usrak.core.dependencies.config_provider import get_app_config, get_router_config

if TYPE_CHECKING:
    from usrak.core.config_schemas import AppConfig, RouterConfig


class MailSignupManager:
    def __init__(
            self,
            session: Session = Depends(get_db),
            app_config: "AppConfig" = Depends(get_app_config),
            router_config: "RouterConfig" = Depends(get_router_config),
            one_time_tokens_manager: OneTimeTokensManager = Depends(OneTimeTokensManager)
    ):
        self.session = session
        self.app_config = app_config
        self.router_config = router_config
        self.tokens_manager = one_time_tokens_manager

    def _get_user_by_email(self, email: str) -> UserModelBase:
        User = get_user_model()
        user = self.session.exec(select(User).where(User.email == email)).first()
        if not user or user.auth_provider != "email":
            raise exc.InvalidCredentialsException

        return user

    async def signup(
            self,
            email: str,
            plain_password: str,
            auth_provider: str,
            is_active: bool = False,
            is_verified: bool = False,
    ) -> UserModelBase:
        if auth_provider != "email":
            raise exc.UnsupportedAuthProvider

        User = get_user_model()
        UserRead = get_user_read_schema()

        user = self.session.exec(select(User).where(User.email == email)).first()
        if user:
            if user.is_verified:
                raise exc.UserAlreadyExistsException

            else:
                raise exc.UserNotVerifiedException

        new_user = User(
            email=email,
            user_identifier=gen_internal_id(),
            auth_provider=auth_provider,
            hashed_password=hash_password(plain_password),
            is_active=is_active,
            is_verified=is_verified,
            signed_up_at=datetime.now(timezone.utc),
            password_version=1,
        )
        self.session.add(new_user)
        self.session.commit()

        return UserRead.from_orm(new_user)  # type: ignore[return-value]

    async def send_link(self, email: str, plain_password: str):
        user = self._get_user_by_email(email)
        if user.is_verified or user.is_active:
            raise exc.VerificationFailedException

        if not verify_password(plain_password, user.hashed_password):
            raise exc.InvalidCredentialsException

        wait_time = await self.tokens_manager.get_create_wait_time(email)
        if wait_time > 0:
            raise exc.MailSendRateLimitException(wait_time)

        verify_wait_time = await self.tokens_manager.get_verify_wait_time(email)
        if verify_wait_time > 0:
            raise exc.MailSendRateLimitException(verify_wait_time)

        token = await self.tokens_manager.create_one_time_token(
            user_identifier=user.user_identifier,
            exp=self.app_config.EMAIL_VERIFICATION_LINK_EXPIRE_SEC,
            password_version=user.password_version,
            purpose="signup",
        )

        notification_service = deps.get_notification_service()
        status = await notification_service.send_signup_verification(
            email=email,
            token=token,
        )
        if not status:
            raise exc.MailSendFailedException(f"Failed to send signup email to {email}.")

    async def verify(self, email: str, token: str):
        user = self._get_user_by_email(email)
        if user.is_active:
            raise exc.VerificationFailedException

        # token_valid = await self.tokens_manager.validate_token(
        #     token=token,
        #     user_identifier=user.internal_id,
        #     password_version=user.password_version,
        # )
        # TODO: use validate token from one time manager
        #     raise exc.VerificationFailedException

        user.is_active = True
        user.is_verified = True

        self.session.add(user)
        self.session.commit()
