from enum import Enum

import pytest
from pydantic import ValidationError

from usrak import AppConfig, DefaultRoles, RouterConfig
from usrak.core.dependencies.config_provider import get_app_config, set_app_config, get_router_config, \
    set_router_config, app_config as global_app_config, router_config as global_router_config
from usrak.core.managers.key_value_store import InMemoryKeyValueStore, RedisKeyValueStore, LMDBKeyValueStore
from usrak.core.managers.notification.no_op import NoOpNotificationService
from usrak.core.managers.notification.smtp import SmtpNotificationService
from usrak.core.managers.rate_limiter.no_op import NoOpFastApiRateLimiter
from usrak.core.smtp.no_op import NoOpSMTPClient

from .fixtures.tokens import TestTokensModel, TestTokensReadSchema
from .fixtures.user import TestRoleModel, TestUserModel, TestUserReadSchema


class CustomRoles(str, Enum):
    ADMIN = "superuser"
    USER = "member"
    AUDITOR = "auditor"


class MissingUserRoles(str, Enum):
    ADMIN = "admin"


def make_router_config(**overrides) -> RouterConfig:
    defaults = {
        "USER_MODEL": TestUserModel,
        "USER_READ_SCHEMA": TestUserReadSchema,
        "USER_IDENTIFIER_FIELD_NAME": "super_id",
        "TOKENS_MODEL": TestTokensModel,
        "TOKENS_READ_SCHEMA": TestTokensReadSchema,
    }
    defaults.update(overrides)
    return RouterConfig(**defaults)


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
    assert router_config.DEFAULT_ROLES_ENUM is DefaultRoles
    assert router_config.ENABLE_ADMIN_PANEL is True  # Значение по умолчанию


def test_router_config_missing_required_fields():
    """Тестирует, что RouterConfig вызывает ошибку при отсутствии обязательных полей."""
    with pytest.raises(ValidationError):
        RouterConfig()  # type: ignore

    with pytest.raises(ValidationError):
        RouterConfig(USER_MODEL=TestUserModel)  # type: ignore


def test_router_config_kvs_validation():
    """Тестирует валидацию KEY_VALUE_STORE в RouterConfig."""
    cfg_in_memory = make_router_config(KEY_VALUE_STORE="in_memory")
    assert cfg_in_memory.KEY_VALUE_STORE is InMemoryKeyValueStore

    cfg_redis = make_router_config(KEY_VALUE_STORE="redis")
    assert cfg_redis.KEY_VALUE_STORE is RedisKeyValueStore

    cfg_lmdb = make_router_config(KEY_VALUE_STORE="lmdb")
    assert cfg_lmdb.KEY_VALUE_STORE is LMDBKeyValueStore

    with pytest.raises(ValueError, match="Unknown KeyValueStore type: unknown_kvs"):
        make_router_config(KEY_VALUE_STORE="unknown_kvs")


def test_router_config_notification_service_validation():
    """Тестирует валидацию NOTIFICATION_SERVICE в RouterConfig."""
    cfg_noop = make_router_config(NOTIFICATION_SERVICE="no_op")
    assert cfg_noop.NOTIFICATION_SERVICE is NoOpNotificationService

    cfg_smtp = make_router_config(NOTIFICATION_SERVICE="smtp")
    assert cfg_smtp.NOTIFICATION_SERVICE is SmtpNotificationService

    cfg_none = make_router_config(NOTIFICATION_SERVICE=None)
    assert cfg_none.NOTIFICATION_SERVICE is NoOpNotificationService

    with pytest.raises(ValueError, match="Unknown NotificationService type: unknown_service"):
        make_router_config(NOTIFICATION_SERVICE="unknown_service")


def test_router_config_fast_api_rate_limiter_validation():
    """Тестирует валидацию FAST_API_RATE_LIMITER в RouterConfig."""
    cfg_noop = make_router_config(FAST_API_RATE_LIMITER="no_op")
    assert cfg_noop.FAST_API_RATE_LIMITER is NoOpFastApiRateLimiter

    cfg_none = make_router_config(FAST_API_RATE_LIMITER=None)
    assert cfg_none.FAST_API_RATE_LIMITER is NoOpFastApiRateLimiter

    with pytest.raises(NotImplementedError):
        # TODO: Remove after RedisFastApiRateLimiter implementation
        make_router_config(FAST_API_RATE_LIMITER="redis")

    with pytest.raises(ValueError, match="Unknown FastApiRateLimiter type: unknown_limiter"):
        make_router_config(FAST_API_RATE_LIMITER="unknown_limiter")


def test_router_config_smtp_client_validation():
    """Тестирует валидацию SMTP_CLIENT в RouterConfig."""
    smtp_client_module = pytest.importorskip("usrak.core.smtp.client")
    smtp_client_cls = smtp_client_module.SMTPClient

    cfg_noop = make_router_config(SMTP_CLIENT="no_op")
    assert cfg_noop.SMTP_CLIENT is NoOpSMTPClient

    cfg_default = make_router_config(SMTP_CLIENT="default")
    assert cfg_default.SMTP_CLIENT is smtp_client_cls

    cfg_none = make_router_config(SMTP_CLIENT=None)
    assert cfg_none.SMTP_CLIENT is NoOpSMTPClient

    with pytest.raises(ValueError, match="Unknown SMTPClient type: unknown_client"):
        make_router_config(SMTP_CLIENT="unknown_client")


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
    cfg_default = make_router_config()
    assert not cfg_default.ENABLE_OAUTH
    assert not cfg_default.ENABLE_GOOGLE_OAUTH
    assert not cfg_default.ENABLE_TELEGRAM_OAUTH

    # Если ENABLE_OAUTH = True, остальные могут быть True
    cfg_oauth_enabled = make_router_config(
        ENABLE_OAUTH=True,
        ENABLE_GOOGLE_OAUTH=True,
        ENABLE_TELEGRAM_OAUTH=True,
    )
    assert cfg_oauth_enabled.ENABLE_OAUTH
    assert cfg_oauth_enabled.ENABLE_GOOGLE_OAUTH
    assert cfg_oauth_enabled.ENABLE_TELEGRAM_OAUTH

    # Если ENABLE_OAUTH = True, но конкретный провайдер False
    cfg_oauth_partial = make_router_config(
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
    cfg_oauth_false_explicit_true = make_router_config(
        ENABLE_OAUTH=False,
        ENABLE_GOOGLE_OAUTH=True,  # Это значение будет установлено
        ENABLE_TELEGRAM_OAUTH=True  # И это
    )
    assert not cfg_oauth_false_explicit_true.ENABLE_OAUTH
    assert cfg_oauth_false_explicit_true.ENABLE_GOOGLE_OAUTH  # Остается True, как передано
    assert cfg_oauth_false_explicit_true.ENABLE_TELEGRAM_OAUTH  # Остается True, как передано


def test_router_config_redis_flags_dependency():
    """Тестирует зависимость флагов использования Redis от ENABLE_REDIS_CLIENT."""
    cfg_default = make_router_config()
    assert not cfg_default.ENABLE_REDIS_CLIENT
    assert not cfg_default.USE_REDIS_FOR_RATE_LIMITING
    assert not cfg_default.USE_REDIS_FOR_KV_STORE

    cfg_redis_enabled = make_router_config(
        ENABLE_REDIS_CLIENT=True,
        USE_REDIS_FOR_RATE_LIMITING=True,
        USE_REDIS_FOR_KV_STORE=True,
    )
    assert cfg_redis_enabled.ENABLE_REDIS_CLIENT
    assert cfg_redis_enabled.USE_REDIS_FOR_RATE_LIMITING
    assert cfg_redis_enabled.USE_REDIS_FOR_KV_STORE

    # Аналогично OAuth, если ENABLE_REDIS_CLIENT=False, но дочерние флаги переданы как True, они останутся True.
    cfg_redis_false_explicit_true = make_router_config(
        ENABLE_REDIS_CLIENT=False,
        USE_REDIS_FOR_RATE_LIMITING=True,  # Будет True
        USE_REDIS_FOR_KV_STORE=True  # Будет True
    )
    assert not cfg_redis_false_explicit_true.ENABLE_REDIS_CLIENT
    assert cfg_redis_false_explicit_true.USE_REDIS_FOR_RATE_LIMITING
    assert cfg_redis_false_explicit_true.USE_REDIS_FOR_KV_STORE


def test_router_config_user_identifier():
    cfg = make_router_config()
    assert cfg.USER_IDENTIFIER_FIELD_NAME == "super_id"

    with pytest.raises(ValidationError,
                       match="USER_MODEL must have field 'non_existent_field', defined in USER_IDENTIFIER_FIELD_NAME"):
        make_router_config(USER_IDENTIFIER_FIELD_NAME="non_existent_field")


def test_router_config_default_roles_enum_override():
    original_default_role = TestUserModel.__default_role__
    original_role_field_name = TestUserModel.__role_field_name__
    original_id_field_name = TestUserModel.__id_field_name__

    try:
        cfg = make_router_config(DEFAULT_ROLES_ENUM=CustomRoles)

        assert cfg.DEFAULT_ROLES_ENUM is CustomRoles
        assert TestUserModel.__default_role__ == CustomRoles.USER.value
    finally:
        TestUserModel.__default_role__ = original_default_role
        TestUserModel.__role_field_name__ = original_role_field_name
        TestUserModel.__id_field_name__ = original_id_field_name


def test_router_config_default_roles_enum_requires_admin_and_user():
    with pytest.raises(ValidationError, match="DEFAULT_ROLES_ENUM must define members: USER"):
        make_router_config(DEFAULT_ROLES_ENUM=MissingUserRoles)


def test_router_config_default_user_management_rules_default():
    cfg = make_router_config()

    admin_rules = cfg.DEFAULT_USER_MANAGEMENT_RULES[DefaultRoles.ADMIN.value]
    assert admin_rules.create == {DefaultRoles.USER.value}
    assert admin_rules.update == {DefaultRoles.USER.value}
    assert admin_rules.delete == {DefaultRoles.USER.value}


def test_router_config_default_user_management_rules_validation():
    with pytest.raises(ValidationError, match="unknown source role: manager"):
        make_router_config(
            DEFAULT_USER_MANAGEMENT_RULES={
                "manager": {
                    "create": {"user"},
                    "update": {"user"},
                    "delete": {"user"},
                }
            }
        )

    with pytest.raises(ValidationError, match="unknown target roles: manager"):
        make_router_config(
            DEFAULT_USER_MANAGEMENT_RULES={
                "admin": {
                    "create": {"manager"},
                    "update": {"user"},
                    "delete": {"user"},
                }
            }
        )


def test_router_config_role_model_override():
    cfg = make_router_config(ROLE_MODEL=TestRoleModel)
    assert cfg.ROLE_MODEL is TestRoleModel
