from typing import Optional, TYPE_CHECKING

from fastapi import Depends

from usrak.core.dependencies.config_provider import get_app_config, get_router_config


if TYPE_CHECKING:
    from usrak.core.config_schemas import AppConfig, RouterConfig


class ConfigDependencyMixin:
    _app_config: Optional["AppConfig"] = None
    _router_config: Optional["RouterConfig"] = None

    def __new__(
            cls,
            app_config: "AppConfig" = Depends(get_app_config),
            router_config: "RouterConfig" = Depends(get_router_config),
    ):
        instance = super().__new__(cls)
        instance._app_config = app_config
        instance._router_config = router_config
        return instance

    @property
    def app_config(self) -> "AppConfig":
        if self._app_config is None:
            raise RuntimeError("AppConfig is not set yet.")
        return self._app_config

    @property
    def router_config(self) -> "RouterConfig":
        if self._router_config is None:
            raise RuntimeError("RouterConfig is not set yet.")
        return self._router_config

    @property
    def kvs(self):
        return self.router_config.KEY_VALUE_STORE(
            app_config=self.app_config,
            router_config=self.router_config
        )
