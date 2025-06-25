from typing import List, Optional, Literal

from pydantic import BaseModel, Field
from pydantic import PostgresDsn, RedisDsn, EmailStr
from pydantic import field_validator

from usrak.core.managers.key_value_store import LMDBKeyValueStore
from usrak.core.managers.notification.no_op import NoOpNotificationService
from usrak.core.managers.rate_limiter.no_op import NoOpFastApiRateLimiter
from usrak.core.smtp.no_op import NoOpSMTPClient
from usrak import providers_type as pt


class RouterConfig(BaseModel):

    USER_MODEL: pt.UserModelType = Field(
        ..., description="User's SQLModel class redefined from 'UserModelBase'"
    )
    USER_READ_SCHEMA: pt.UserReadSchemaType = Field(
        ..., description="User's read schema class redefined from user's SQLModel class ('USER_MODEL')"
    )
    KEY_VALUE_STORE: pt.KeyValueStoreType | Literal["in_memory", "redis", "lmdb"] = Field(
        default=LMDBKeyValueStore, description="KeyValueStore class"
    )
    NOTIFICATION_SERVICE: pt.NotificationServiceType | Literal["smtp", "no_op"] | None = Field(
        default=NoOpNotificationService, description="NotificationService class"
    )
    FAST_API_RATE_LIMITER: pt.FastApiRateLimiterType | Literal["redis", "no_op"] | None = Field(
        default=NoOpFastApiRateLimiter, description="FastApiRateLimiter class"
    )
    SMTP_CLIENT: pt.SMTPClientType | Literal["default", "no_op"] | None = Field(
        default=NoOpSMTPClient, description="SMTPClient class"
    )

    ENABLE_ADMIN_PANEL: bool = True

    # --- Флаги основного функционала ---
    ENABLE_EMAIL_REGISTRATION: bool = False  # Включает/отключает регистрацию по email
    ENABLE_PASSWORD_RESET_VIA_EMAIL: bool = False  # Включает/отключает сброс пароля по email

    # --- Флаги для OAUTH ---
    ENABLE_OAUTH: bool = False  # Включает/отключает регистрацию по OAuth
    ENABLE_GOOGLE_OAUTH: bool = False if ENABLE_OAUTH else False
    ENABLE_TELEGRAM_OAUTH: bool = False if ENABLE_OAUTH else False

    # --- Флаги для опций верификации и уведомлений ---
    # Если False, то коды/письма не используются. Поведение зависит от AUTO_VERIFY_... флагов.
    USE_VERIFICATION_LINKS_FOR_SIGNUP: bool = False
    USE_LINKS_FOR_PASSWORD_RESET: bool = False

    # Поведение при отключенных кодах/письмах
    AUTO_VERIFY_USER_ON_SIGNUP_IF_CODES_DISABLED: bool = False
    # Если True и USE_VERIFICATION_CODES_FOR_SIGNUP=False, юзер сразу активен
    # Для сброса пароля: если USE_LINKS_FOR_PASSWORD_RESET=False, то функционал просто отключается.

    # --- Флаги для зависимостей ---
    ENABLE_REDIS_CLIENT: bool = False  # Глобальный флаг для подключения к Redis

    # Использование Redis для конкретных задач (зависят от ENABLE_REDIS_CLIENT)
    USE_REDIS_FOR_RATE_LIMITING: bool = False if ENABLE_REDIS_CLIENT else False
    USE_REDIS_FOR_KV_STORE: bool = False if ENABLE_REDIS_CLIENT else False  # Для кодов, токенов AuthManager и т.д.

    ENABLE_SMTP_CLIENT: bool = False  # Глобальный флаг для SMTP
    # SMTP будет использоваться, если включен соответствующий функционал (коды, сброс пароля) и ENABLE_SMTP_CLIENT=True

    @field_validator("KEY_VALUE_STORE", mode="before")
    @classmethod
    def validate_key_value_store(cls, v: pt.KeyValueStoreType | Literal["in_memory", "redis", "lmdb"]) -> pt.KeyValueStoreType:
        print("validate_key_value_store KEY_VALUE_STORE")
        if isinstance(v, str):
            if v == "in_memory":
                from usrak.core.managers.key_value_store import InMemoryKeyValueStore
                return InMemoryKeyValueStore
            elif v == "redis":
                from usrak.core.managers.key_value_store import RedisKeyValueStore
                return RedisKeyValueStore
            elif v == "lmdb":
                from usrak.core.managers.key_value_store import LMDBKeyValueStore
                return LMDBKeyValueStore
            else:
                raise ValueError(f"Unknown KeyValueStore type: {v}")
        return v

    @field_validator("NOTIFICATION_SERVICE", mode="before")
    @classmethod
    def validate_notification_service(cls, v: pt.NotificationServiceType | Literal["smtp"] | None) -> pt.NotificationServiceType | None:
        if isinstance(v, str):
            if v == "smtp":
                from usrak.core.managers.notification.smtp import SmtpNotificationService
                return SmtpNotificationService
            elif v == "no_op":
                from usrak.core.managers.notification.no_op import NoOpNotificationService
                return NoOpNotificationService
            else:
                raise ValueError(f"Unknown NotificationService type: {v}")
        if v is None:
            from usrak.core.managers.notification.no_op import NoOpNotificationService
            return NoOpNotificationService
        return v

    @field_validator("FAST_API_RATE_LIMITER", mode="before")
    @classmethod
    def validate_fast_api_rate_limiter(cls, v: pt.FastApiRateLimiterType | Literal["redis"] | None) -> pt.FastApiRateLimiterType | None:
        if isinstance(v, str):
            if v == "redis":
                # TODO: Implement RedisFastApiRateLimiter
                raise NotImplementedError
            elif v == "no_op":
                from usrak.core.managers.rate_limiter.no_op import NoOpFastApiRateLimiter
                return NoOpFastApiRateLimiter
            else:
                raise ValueError(f"Unknown FastApiRateLimiter type: {v}")
        if v is None:
            from usrak.core.managers.rate_limiter.no_op import NoOpFastApiRateLimiter
            return NoOpFastApiRateLimiter
        return v

    @field_validator("SMTP_CLIENT", mode="before")
    @classmethod
    def validate_smtp_client(cls, v: pt.SMTPClientType | Literal["default", "no_op"] | None) -> pt.SMTPClientType | None:
        if isinstance(v, str):
            if v == "default":
                from usrak.core.smtp.client import SMTPClient
                return SMTPClient
            elif v == "no_op":
                from usrak.core.smtp.no_op import NoOpSMTPClient
                return NoOpSMTPClient
            else:
                raise ValueError(f"Unknown SMTPClient type: {v}")
        if v is None:
            from usrak.core.smtp.no_op import NoOpSMTPClient
            return NoOpSMTPClient
        return v

    def __hash__(self):
        return hash(tuple(sorted(self.dict().items())))


class AppConfig(BaseModel):
    PROJECT_NAME: str = "Auth Service"

    TRUSTED_PROXIES: List[str] = ["127.0.0.1"]
    MAIN_DOMAIN: str = "127.0.0.1"
    ALLOW_ORIGINS: List[str] = ["http://localhost:5173"]
    EXPOSE_HEADERS: List[str] = ["retry-after", "cool-down"]

    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "lax"

    GATEWAY_HOST: str = "127.0.0.1"
    GATEWAY_PORT: int = 8200

    REDIRECT_AFTER_AUTH_URL: str = ""

    DATABASE_URL: PostgresDsn
    REDIS_URL: Optional[RedisDsn] = None

    LMDB_PATH: Optional[str] = "./data/lmdb"  # Default path for LMDB storage
    LMDB_DEFAULT_TTL: int = 1 * 60 * 60  # 1 hour
    LMDB_MAP_SIZE: int = 2**30
    LMDB_CLEANUP_INTERVAL: int = 12 * 60 * 60  # 12 hours

    JWT_ACCESS_TOKEN_SECRET_KEY: str
    JWT_REFRESH_TOKEN_SECRET_KEY: str
    JWT_ONETIME_TOKEN_SECRET_KEY: str

    ALGORITHM: str = "HS256"
    CODE_HASH_SALT: str
    FERNET_KEY: str

    ACCESS_TOKEN_EXPIRE_SEC: int = 15 * 60
    REFRESH_TOKEN_EXPIRE_SEC: int = 7 * 60 * 60 * 24
    EMAIL_VERIFICATION_LINK_EXPIRE_SEC: int = 30 * 60
    PASSWORD_RESET_LINK_EXPIRE_SEC: int = 30 * 60

    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None

    GOOGLE_AUTH_URL: str = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL: str = "https://www.googleapis.com/oauth2/v3/userinfo"

    TELEGRAM_AUTH_BOT_TOKEN: Optional[str] = None

    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_SENDER_EMAIL: Optional[EmailStr] = None
    SMTP_SENDER_NAME: str = "Auth Service"

    LOGIN_RATE_LIMIT_TIMES: int = 3
    LOGIN_RATE_LIMIT_SECONDS: int = 60

    SIGNUP_RATE_LIMIT_TIMES: int = 3
    SIGNUP_RATE_LIMIT_SECONDS: int = 60 * 30

    LOGOUT_RATE_LIMIT_TIMES: int = 3
    LOGOUT_RATE_LIMIT_SECONDS: int = 60 * 30

    REFRESH_TOKEN_RATE_LIMIT_TIMES: int = 3
    REFRESH_TOKEN_RATE_LIMIT_SECONDS: int = 60 * 30

    RESET_PASSWORD_RATE_LIMIT_TIMES: int = 4
    RESET_PASSWORD_RATE_LIMIT_SECONDS: int = 60 * 60

    REQUEST_RESET_CODE_RATE_LIMIT_TIMES: int = 3
    REQUEST_RESET_CODE_RATE_LIMIT_SECONDS: int = 60 * 30

    REQUEST_SIGNUP_CODE_RATE_LIMIT_TIMES: int = 3
    REQUEST_SIGNUP_CODE_RATE_LIMIT_SECONDS: int = 60 * 30

    VERIFY_SIGNUP_RATE_LIMIT_TIMES: int = 3
    VERIFY_SIGNUP_RATE_LIMIT_SECONDS: int = 60 * 30

    OAUTH_RATE_LIMIT_TIMES: int = 3
    OAUTH_RATE_LIMIT_SECONDS: int = 60 * 30

    MAX_ONE_TIME_CODE_CREATE_ATTEMPTS: int = 4
    ONE_TIME_TOKEN_TTL: int = 60 * 30

    DEFAULT_KVS_TTL: int = 60 * 60 * 24

    MAX_MAIL_CREATE_LINK_ATTEMPTS: int = 4
    MAIL_LINK_TTL: int = 60 * 30

    PASSWORD_CHANGE_COOLDOWN_SEC: int = 60 * 60 * 12
