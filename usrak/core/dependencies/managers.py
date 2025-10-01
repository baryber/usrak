from functools import lru_cache
from typing import TYPE_CHECKING

from ... import providers_type as pt

from usrak.core.dependencies.config_provider import get_router_config

if TYPE_CHECKING:
    from usrak.core.config_schemas import AppConfig, RouterConfig


@lru_cache()
def get_user_model() -> pt.UserModelType:
    config = get_router_config()
    return config.USER_MODEL


@lru_cache()
def get_user_read_schema() -> pt.UserReadSchemaType:
    config = get_router_config()
    return config.USER_READ_SCHEMA


@lru_cache()
def get_tokens_model() -> pt.TokensModelType:
    config = get_router_config()
    return config.TOKENS_MODEL


@lru_cache()
def get_tokens_read_schema() -> pt.TokensReadSchemaType:
    config = get_router_config()
    return config.TOKENS_READ_SCHEMA


@lru_cache()
def get_key_value_store() -> pt.KeyValueStoreABS:
    config = get_router_config()
    return config.KEY_VALUE_STORE()


@lru_cache()
def get_notification_service() -> pt.NotificationServiceABS:
    config = get_router_config()
    return config.NOTIFICATION_SERVICE()


@lru_cache()
def get_smtp_client() -> pt.SMTPClientABS:
    config = get_router_config()
    return config.SMTP_CLIENT()
