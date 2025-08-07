import time
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from usrak.core.redis.client import redis
from usrak.core import exceptions as exc
from usrak.core.models.user import UserModelBase
from usrak.core.security import hash_password
from usrak.core.templates.mail import reset_password_link_mail
from usrak.core.dependencies.config_provider import get_router_config, get_app_config
from usrak.core._rate_limit.mail_link import MailLinkRateLimiter


class PasswordResetManager:
    REDIS_PREFIX = "password_reset_token"

    def __init__(self, session: Session):
        self.session = session
        self.rate_limiter = MailLinkRateLimiter(
            redis_prefix=self.REDIS_PREFIX,
            redis_client=redis
        )

    def _get_user_by_email(self, email: str) -> UserModelBase:
        confif = get_app_config()
        UserModel = confif.USER_MODEL

        user = self.session.exec(select(UserModel).where(UserModel.email == email)).first()
        if not user or user.auth_provider != "email":
            raise exc.InvalidCredentialsException

        return user

    async def _get_change_cool_down(self, user: UserModelBase) -> int:
        config = get_app_config()

        last_change = user.last_password_change
        if not last_change:
            return 0

        wait_time = (last_change + timedelta(seconds=config.PASSWORD_CHANGE_COOLDOWN_SEC)) - datetime.now(timezone.utc)

        if wait_time.total_seconds() > 0:
            return wait_time.seconds

        return 0

    async def send_link(self, email: str):
        config = get_app_config()

        user = self._get_user_by_email(email)
        if not user:
            raise exc.InvalidCredentialsException

        if not user.is_verified or not user.is_active:
            raise exc.VerificationFailedException

        cool_down = await self._get_change_cool_down(user)
        if cool_down > 0:
            raise exc.PasswordChangeCoolDownException(cool_down)

        verification_wait_time = await self.rate_limiter.get_verify_wait_time(email)
        if verification_wait_time > 0:
            raise exc.MailSendRateLimitException(verification_wait_time)

        reset_token = await self.rate_limiter.create_link(
            user_identifier=user.user_identifier,
            password_version=user.password_version
        )

        mail = reset_password_link_mail(
            receiver=email,
            token=reset_token,
            token_expire_timestamp=int(time.time()) + config.PASSWORD_RESET_LINK_EXPIRE_SEC
        )
        print(mail)

        # success, msg = await mail_client.send_mail(mail)
        # if not success:
        #     raise exc.MailSendFailedException(msg)

    async def verify_token(
            self,
            email: str,
            reset_token: str,
    ) -> bool:
        user = self._get_user_by_email(email)
        if not user.is_verified or not user.is_active:
            raise exc.VerificationFailedException

        if not await self.rate_limiter.verify_link(
            user_identifier=user.user_identifier,
            password_version=user.password_version,
            token=reset_token
        ):
            raise exc.InvalidTokenException

        wait_time = await self._get_change_cool_down(user)
        if wait_time > 0:
            raise exc.PasswordChangeCoolDownException(wait_time)

        return True

    async def reset(
            self,
            email: str,
            reset_token: str,
            new_password: str
    ):
        if not await self.verify_token(
            email=email,
            reset_token=reset_token
        ):
            raise exc.InvalidTokenException

        user = self._get_user_by_email(email)
        if not user.is_verified or not user.is_active:
            raise exc.VerificationFailedException

        user.hashed_password = hash_password(new_password)
        user.password_version = user.password_version + 1
        user.last_password_change = datetime.now(timezone.utc)

        self.session.add(user)
        self.session.commit()

        await self.rate_limiter.cleanup(user_identifier=user.user_identifier)
