from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from .core.middleware.save_request import SaveRequestBodyASGIMiddleware
from .core.middleware.trusted_host import TrustedHostMiddleware
from .core.handlers.excpetion import validation_exception_handler

from .core.dependencies.config_provider import get_router_config, get_app_config
from .core.dependencies.config_provider import set_router_config, set_app_config

from .auth_router import AuthRouter
from .core.config_schemas import AppConfig, RouterConfig


class AuthApp(FastAPI):
    def __init__(
            self,
            app_config: AppConfig,
            router_config: RouterConfig,
            **kwargs
    ):
        set_app_config(app_config)
        set_router_config(router_config)

        super().__init__(**kwargs)

        auth_router_instance = AuthRouter(router_config=router_config)

        self.include_router(auth_router_instance)
        self.register_handlers()
        self.register_middlewares()

    def register_handlers(self):
        self.add_exception_handler(RequestValidationError, validation_exception_handler)

    def register_middlewares(self):
        config = get_app_config()

        self.add_middleware(
            CORSMiddleware,
            allow_origins=config.ALLOW_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=config.EXPOSE_HEADERS
        )
        self.add_middleware(SaveRequestBodyASGIMiddleware)
        self.add_middleware(TrustedHostMiddleware, trusted_proxies=config.TRUSTED_PROXIES)
