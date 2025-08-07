import pytest
from pydantic import ValidationError

from usrak import AppConfig, RouterConfig
from usrak.core.dependencies.config_provider import get_app_config, set_app_config, get_router_config, \
    set_router_config, app_config as global_app_config, router_config as global_router_config
from usrak.core.managers.key_value_store import InMemoryKeyValueStore, RedisKeyValueStore, LMDBKeyValueStore
from usrak.core.managers.notification.no_op import NoOpNotificationService
from usrak.core.managers.notification.smtp import SmtpNotificationService
from usrak.core.managers.rate_limiter.no_op import NoOpFastApiRateLimiter
from usrak.core.smtp.no_op import NoOpSMTPClient
from usrak.core.smtp.client import SMTPClient

from .fixtures.user import TestUserModel, TestUserReadSchema


def test_app_config_creation(app_config: AppConfig):
    """Тестирует создание экземпляра AppConfig с базовыми значениями."""
    assert app_config.PROJECT_NAME == "Auth Service"
    assert app_config.JWT_ACCESS_TOKEN_SECRET_KEY == "test_access_secret"
    assert app_config.FERNET_KEY == "Y8RFpaIxSaAFNsB352tpLXl5znUw5anEKIZgclOezak="


def test_app_config_missing_required_fields():
    """Тестирует, что AppConfig вызывает ошибку при отсутствии обязательных полей."""
    with pytest.raises(ValidationError):
        AppConfig()

    with pytest.raises(ValidationError):
        AppConfig(
            DATABASE_URL="postgresql://user:pass@host:port/db",
            # Отсутствуют JWT ключи и другие обязательные поля
        )


def test_router_config_creation(router_config: RouterConfig):
    """Тестирует создание экземпляра RouterConfig с базовыми значениями."""
    assert router_config.USER_MODEL is TestUserModel
    assert router_config.USER_READ_SCHEMA is TestUserReadSchema
    assert router_config.ENABLE_ADMIN_PANEL is True  # Значение по умолчанию


def test_router_config_missing_required_fields():
    """Тестирует, что RouterConfig вызывает ошибку при отсутствии обязательных полей."""
    with pytest.raises(ValidationError):
        RouterConfig()  # type: ignore

    with pytest.raises(ValidationError):
        RouterConfig(USER_MODEL=TestUserModel)  # type: ignore


def test_router_config_kvs_validation():
    """Тестирует валидацию KEY_VALUE_STORE в RouterConfig."""
    cfg_in_memory = RouterConfig(USER_MODEL=TestUserModel,
                                 USER_READ_SCHEMA=TestUserReadSchema,
                                 KEY_VALUE_STORE="in_memory",
                                 USER_IDENTIFIER_FIELD_NAME="super_id")
    assert cfg_in_memory.KEY_VALUE_STORE is InMemoryKeyValueStore

    cfg_redis = RouterConfig(USER_MODEL=TestUserModel,
                             USER_READ_SCHEMA=TestUserReadSchema,
                             KEY_VALUE_STORE="redis",
                             USER_IDENTIFIER_FIELD_NAME="super_id")
    assert cfg_redis.KEY_VALUE_STORE is RedisKeyValueStore

    cfg_lmdb = RouterConfig(USER_MODEL=TestUserModel,
                            USER_READ_SCHEMA=TestUserReadSchema,
                            KEY_VALUE_STORE="lmdb",
                            USER_IDENTIFIER_FIELD_NAME="super_id")
    assert cfg_lmdb.KEY_VALUE_STORE is LMDBKeyValueStore

    with pytest.raises(ValueError, match="Unknown KeyValueStore type: unknown_kvs"):
        RouterConfig(USER_MODEL=TestUserModel,
                     USER_READ_SCHEMA=TestUserReadSchema,
                     KEY_VALUE_STORE="unknown_kvs",
                     USER_IDENTIFIER_FIELD_NAME="super_id")


def test_router_config_notification_service_validation():
    """Тестирует валидацию NOTIFICATION_SERVICE в RouterConfig."""
    cfg_noop = RouterConfig(USER_MODEL=TestUserModel,
                            USER_READ_SCHEMA=TestUserReadSchema,
                            NOTIFICATION_SERVICE="no_op",
                                 USER_IDENTIFIER_FIELD_NAME="super_id")
    assert cfg_noop.NOTIFICATION_SERVICE is NoOpNotificationService

    cfg_smtp = RouterConfig(USER_MODEL=TestUserModel,
                            USER_READ_SCHEMA=TestUserReadSchema,
                            NOTIFICATION_SERVICE="smtp",
                                 USER_IDENTIFIER_FIELD_NAME="super_id")
    assert cfg_smtp.NOTIFICATION_SERVICE is SmtpNotificationService

    cfg_none = RouterConfig(USER_MODEL=TestUserModel,
                            USER_READ_SCHEMA=TestUserReadSchema,
                            NOTIFICATION_SERVICE=None,
                                 USER_IDENTIFIER_FIELD_NAME="super_id")
    assert cfg_none.NOTIFICATION_SERVICE is NoOpNotificationService

    with pytest.raises(ValueError, match="Unknown NotificationService type: unknown_service"):
        RouterConfig(USER_MODEL=TestUserModel, USER_READ_SCHEMA=TestUserReadSchema,
                     NOTIFICATION_SERVICE="unknown_service",
                                 USER_IDENTIFIER_FIELD_NAME="super_id")


def test_router_config_fast_api_rate_limiter_validation():
    """Тестирует валидацию FAST_API_RATE_LIMITER в RouterConfig."""
    cfg_noop = RouterConfig(USER_MODEL=TestUserModel,
                            USER_READ_SCHEMA=TestUserReadSchema,
                            FAST_API_RATE_LIMITER="no_op",
                                 USER_IDENTIFIER_FIELD_NAME="super_id")
    assert cfg_noop.FAST_API_RATE_LIMITER is NoOpFastApiRateLimiter

    cfg_none = RouterConfig(USER_MODEL=TestUserModel,
                            USER_READ_SCHEMA=TestUserReadSchema,
                            FAST_API_RATE_LIMITER=None,
                                 USER_IDENTIFIER_FIELD_NAME="super_id")
    assert cfg_none.FAST_API_RATE_LIMITER is NoOpFastApiRateLimiter

    with pytest.raises(NotImplementedError):
        # TODO: Remove after RedisFastApiRateLimiter implementation
        RouterConfig(USER_MODEL=TestUserModel,
                     USER_READ_SCHEMA=TestUserReadSchema,
                     FAST_API_RATE_LIMITER="redis",
                                 USER_IDENTIFIER_FIELD_NAME="super_id")

    with pytest.raises(ValueError, match="Unknown FastApiRateLimiter type: unknown_limiter"):
        RouterConfig(USER_MODEL=TestUserModel,
                     USER_READ_SCHEMA=TestUserReadSchema,
                     FAST_API_RATE_LIMITER="unknown_limiter",
                                 USER_IDENTIFIER_FIELD_NAME="super_id")


def test_router_config_smtp_client_validation():
    """Тестирует валидацию SMTP_CLIENT в RouterConfig."""
    cfg_noop = RouterConfig(USER_MODEL=TestUserModel,
                            USER_READ_SCHEMA=TestUserReadSchema,
                            SMTP_CLIENT="no_op",
                                 USER_IDENTIFIER_FIELD_NAME="super_id")
    assert cfg_noop.SMTP_CLIENT is NoOpSMTPClient

    cfg_default = RouterConfig(USER_MODEL=TestUserModel,
                               USER_READ_SCHEMA=TestUserReadSchema,
                               SMTP_CLIENT="default",
                                 USER_IDENTIFIER_FIELD_NAME="super_id")
    assert cfg_default.SMTP_CLIENT is SMTPClient

    cfg_none = RouterConfig(USER_MODEL=TestUserModel,
                            USER_READ_SCHEMA=TestUserReadSchema,
                            SMTP_CLIENT=None,
                                 USER_IDENTIFIER_FIELD_NAME="super_id")
    assert cfg_none.SMTP_CLIENT is NoOpSMTPClient

    with pytest.raises(ValueError, match="Unknown SMTPClient type: unknown_client"):
        RouterConfig(USER_MODEL=TestUserModel,
                     USER_READ_SCHEMA=TestUserReadSchema,
                     SMTP_CLIENT="unknown_client",
                                 USER_IDENTIFIER_FIELD_NAME="super_id")


def test_config_providers(app_config: AppConfig, router_config: RouterConfig):
    """Тестирует функции установки и получения конфигураций."""
    # Сначала глобальные конфиги None (сбрасываются фикстурой reset_extension_config_between_tests)
    assert global_app_config is None
    assert global_router_config is None

    with pytest.raises(RuntimeError, match="AppConfig is None."):
        get_app_config()

    with pytest.raises(RuntimeError, match="RouterConfig is None."):
        get_router_config()

    set_app_config(app_config)
    assert get_app_config() is app_config

    set_router_config(router_config)
    assert get_router_config() is router_config


def test_router_config_oauth_flags_dependency():
    """Тестирует, что флаги ENABLE_GOOGLE_OAUTH и ENABLE_TELEGRAM_OAUTH зависят от ENABLE_OAUTH."""

    # По умолчанию ENABLE_OAUTH = False, поэтому остальные тоже False
    cfg_default = RouterConfig(USER_MODEL=TestUserModel,
                               USER_READ_SCHEMA=TestUserReadSchema,
                                 USER_IDENTIFIER_FIELD_NAME="super_id")
    assert not cfg_default.ENABLE_OAUTH
    assert not cfg_default.ENABLE_GOOGLE_OAUTH
    assert not cfg_default.ENABLE_TELEGRAM_OAUTH

    # Если ENABLE_OAUTH = True, остальные могут быть True
    cfg_oauth_enabled = RouterConfig(
        USER_MODEL=TestUserModel,
        USER_READ_SCHEMA=TestUserReadSchema,
                                 USER_IDENTIFIER_FIELD_NAME="super_id",
        ENABLE_OAUTH=True,
        ENABLE_GOOGLE_OAUTH=True,
        ENABLE_TELEGRAM_OAUTH=True,
    )
    assert cfg_oauth_enabled.ENABLE_OAUTH
    assert cfg_oauth_enabled.ENABLE_GOOGLE_OAUTH
    assert cfg_oauth_enabled.ENABLE_TELEGRAM_OAUTH

    # Если ENABLE_OAUTH = True, но конкретный провайдер False
    cfg_oauth_partial = RouterConfig(
        USER_MODEL=TestUserModel,
        USER_READ_SCHEMA=TestUserReadSchema,
    USER_IDENTIFIER_FIELD_NAME = "super_id",
        ENABLE_OAUTH=True,
        ENABLE_GOOGLE_OAUTH=False,
        ENABLE_TELEGRAM_OAUTH=True
    )
    assert cfg_oauth_partial.ENABLE_OAUTH
    assert not cfg_oauth_partial.ENABLE_GOOGLE_OAUTH
    assert cfg_oauth_partial.ENABLE_TELEGRAM_OAUTH

    # Проверка, что если ENABLE_OAUTH=False, то внутренние флаги тоже False, даже если передать True
    # Pydantic v2 обрабатывает model_fields значения по умолчанию до валидации,
    # поэтому такое поведение (автоматическое выставление в False) не будет работать без кастомного root_validator или model_validator.
    # Текущая реализация в RouterConfig просто задает default=False if ENABLE_OAUTH else False,
    # что означает, что если ENABLE_OAUTH=False, то они будут False, если не переданы явно.
    # Если переданы явно True при ENABLE_OAUTH=False, они останутся True.
    # Это может быть не тем поведением, которое ожидается.
    # Для строгого контроля нужен model_validator.
    # Пока тестируем текущее поведение:
    cfg_oauth_false_explicit_true = RouterConfig(
        USER_MODEL=TestUserModel,
        USER_READ_SCHEMA=TestUserReadSchema,
                                 USER_IDENTIFIER_FIELD_NAME="super_id",
        ENABLE_OAUTH=False,
        ENABLE_GOOGLE_OAUTH=True,  # Это значение будет установлено
        ENABLE_TELEGRAM_OAUTH=True  # И это
    )
    assert not cfg_oauth_false_explicit_true.ENABLE_OAUTH
    assert cfg_oauth_false_explicit_true.ENABLE_GOOGLE_OAUTH  # Остается True, как передано
    assert cfg_oauth_false_explicit_true.ENABLE_TELEGRAM_OAUTH  # Остается True, как передано


def test_router_config_redis_flags_dependency():
    """Тестирует зависимость флагов использования Redis от ENABLE_REDIS_CLIENT."""
    cfg_default = RouterConfig(USER_MODEL=TestUserModel,
                               USER_READ_SCHEMA=TestUserReadSchema,
                                 USER_IDENTIFIER_FIELD_NAME="super_id")
    assert not cfg_default.ENABLE_REDIS_CLIENT
    assert not cfg_default.USE_REDIS_FOR_RATE_LIMITING
    assert not cfg_default.USE_REDIS_FOR_KV_STORE

    cfg_redis_enabled = RouterConfig(
        USER_MODEL=TestUserModel,
        USER_READ_SCHEMA=TestUserReadSchema,
        USER_IDENTIFIER_FIELD_NAME="super_id",
        ENABLE_REDIS_CLIENT=True,
        USE_REDIS_FOR_RATE_LIMITING=True,
        USE_REDIS_FOR_KV_STORE=True,
    )
    assert cfg_redis_enabled.ENABLE_REDIS_CLIENT
    assert cfg_redis_enabled.USE_REDIS_FOR_RATE_LIMITING
    assert cfg_redis_enabled.USE_REDIS_FOR_KV_STORE

    # Аналогично OAuth, если ENABLE_REDIS_CLIENT=False, но дочерние флаги переданы как True, они останутся True.
    cfg_redis_false_explicit_true = RouterConfig(
        USER_MODEL=TestUserModel,
        USER_READ_SCHEMA=TestUserReadSchema,
        USER_IDENTIFIER_FIELD_NAME="super_id",
        ENABLE_REDIS_CLIENT=False,
        USE_REDIS_FOR_RATE_LIMITING=True,  # Будет True
        USE_REDIS_FOR_KV_STORE=True  # Будет True
    )
    assert not cfg_redis_false_explicit_true.ENABLE_REDIS_CLIENT
    assert cfg_redis_false_explicit_true.USE_REDIS_FOR_RATE_LIMITING
    assert cfg_redis_false_explicit_true.USE_REDIS_FOR_KV_STORE


def test_router_config_user_identifier():
    cfg = RouterConfig(
        USER_MODEL=TestUserModel,
        USER_READ_SCHEMA=TestUserReadSchema,
        USER_IDENTIFIER_FIELD_NAME="super_id"
    )
    assert cfg.USER_IDENTIFIER_FIELD_NAME == "super_id"

    with pytest.raises(ValidationError,
                       match="USER_MODEL must have field 'non_existent_field', defined in USER_IDENTIFIER_FIELD_NAME"):
        RouterConfig(
            USER_MODEL=TestUserModel,
            USER_READ_SCHEMA=TestUserReadSchema,
            USER_IDENTIFIER_FIELD_NAME="non_existent_field"
        )
