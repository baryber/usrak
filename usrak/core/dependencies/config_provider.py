from typing import Optional, TYPE_CHECKING

from usrak.core.logger import logger

if TYPE_CHECKING:
    from usrak.core.config_schemas import AppConfig, RouterConfig


app_config: Optional["AppConfig"] = None
router_config: Optional["RouterConfig"] = None


def get_app_config() -> "AppConfig":
    """
    Извлекает конфигурацию приложения.
    Используется для доступа к глобальным настройкам приложения.
    """
    global app_config
    if app_config is None:
        raise RuntimeError(f"AppConfig is None.")
    return app_config


def set_app_config(config: "AppConfig") -> None:
    """
    Помощник для установки конфигурации приложения.
    Вызывается в конструкторе приложения.
    """
    global app_config
    app_config = config
    logger.debug(f"New app config set")


def get_router_config() -> "RouterConfig":
    global router_config
    if router_config is None:
        raise RuntimeError(f"RouterConfig is None.")
    return router_config


def set_router_config(config: "RouterConfig") -> None:
    """
    Помощник для установки конфигурации.
    Вызывается в конструкторе AuthApp или AuthRouter.
    """
    global router_config
    router_config = config
    logger.debug(f"New router config set")
