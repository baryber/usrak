from fastapi import APIRouter

from .routes.login import login_user
from .routes.logout import logout_user
from .routes.refresh import refresh_token
from .routes.user import user_profile
from .routes.check_auth import check_auth

from .core.dependencies import limiters as limiter_deps

from .core.schemas.response import StatusResponse
from .core.config_schemas import RouterConfig


class AuthRouter(APIRouter):
    def __init__(
            self,
            router_config: RouterConfig,
            prefix: str = "",
            tags: list[str] | None = None,
            **kwargs,
    ):
        if tags is None:
            tags = ["auth"]

        super().__init__(**kwargs, prefix=prefix, tags=tags)
        self.router_config = router_config

        self.add_api_route(
            path="/profile",
            endpoint=user_profile,
            methods=["GET"]
        )
        self.add_api_route(
            path="/sign-in",
            endpoint=login_user,
            methods=["POST"],
            response_model=StatusResponse,
            dependencies=limiter_deps.get_login_deps()
        )
        self.add_api_route(
            path="/logout",
            endpoint=logout_user,
            methods=["POST"],
            response_model=StatusResponse,
            dependencies=limiter_deps.get_logout_deps()
        )
        self.add_api_route(
            path="/check-auth",
            endpoint=check_auth,
            methods=["POST"],
            response_model=StatusResponse,
        )

        self.add_api_route(
            path="/refresh",
            endpoint=refresh_token,
            methods=["POST"],
            response_model=StatusResponse,
            dependencies=limiter_deps.get_refresh_token_deps()
        )

        # Register sub-routers based on configuration
        self.register_sub_routers()

    async def startup(self) -> None:
        if self.router_config.ENABLE_SMTP_CLIENT:
            await self.router_config.SMTP_CLIENT().start()

        if self.router_config.ENABLE_REDIS_CLIENT and self.router_config.USE_REDIS_FOR_RATE_LIMITING:
            from core.redis.client import redis
            await self.router_config.FAST_API_RATE_LIMITER.init(redis)

        await super().startup()

    async def shutdown(self) -> None:
        if self.router_config.ENABLE_SMTP_CLIENT:
            await self.router_config.SMTP_CLIENT().stop()

        if self.router_config.ENABLE_REDIS_CLIENT and self.router_config.USE_REDIS_FOR_RATE_LIMITING:
            await self.router_config.FAST_API_RATE_LIMITER.close()

        await super().shutdown()

    def register_sub_routers(self):
        if self.router_config.ENABLE_EMAIL_REGISTRATION:
            from .routes.signup import signup, send_signup_link, verify_signup_link

            sign_up_router = APIRouter(prefix="/signup", tags=["auth"])
            self.include_router(sign_up_router)
            #  Sign up routes
            sign_up_router.add_api_route(
                path="",
                endpoint=signup,
                methods=["POST"],
                response_model=StatusResponse,
                dependencies=limiter_deps.get_signup_deps()
            )
            if self.router_config.USE_VERIFICATION_LINKS_FOR_SIGNUP:
                sign_up_router.add_api_route(
                    path="/send_link",
                    endpoint=send_signup_link,
                    methods=["POST"],
                    response_model=StatusResponse,
                    dependencies=limiter_deps.get_verify_signup_deps()
                )

                sign_up_router.add_api_route(
                    path="/verify",
                    endpoint=verify_signup_link,
                    methods=["POST"],
                    response_model=StatusResponse,
                    dependencies=limiter_deps.get_verify_signup_deps()
                )

        if self.router_config.ENABLE_OAUTH:
            oauth_router = APIRouter(prefix="/oauth", tags=["auth"])
            self.include_router(oauth_router)

            # OAuth routes
            if self.router_config.ENABLE_GOOGLE_OAUTH:
                from .routes.google import google_oauth_callback, google_oauth

                oauth_router.add_api_route(
                    path="/google",
                    endpoint=google_oauth,
                    methods=["POST"],
                    response_model=StatusResponse,
                    dependencies=limiter_deps.get_oauth_deps()
                )
                oauth_router.add_api_route(
                    path="/google/callback",
                    endpoint=google_oauth_callback,
                    methods=["GET"],
                    response_model=StatusResponse,
                    dependencies=limiter_deps.get_oauth_deps()
                )

            if self.router_config.ENABLE_TELEGRAM_OAUTH:
                from .routes.telegram import telegram_auth

                oauth_router.add_api_route(
                    path="/telegram",
                    endpoint=telegram_auth,
                    methods=["POST"],
                    response_model=StatusResponse,
                    dependencies=limiter_deps.get_oauth_deps()
                )

        if self.router_config.ENABLE_PASSWORD_RESET_VIA_EMAIL:
            from .routes.password.forgot import forgot_password
            from .routes.password.change import change_password
            from .routes.password.reset import reset_password, verify_token

            password_router = APIRouter(prefix="/password", tags=["auth"])
            self.include_router(password_router)
            # Password reset routes
            password_router.add_api_route(
                "/forgot", forgot_password, methods=["POST"],
                response_model=StatusResponse,
                dependencies=limiter_deps.get_request_reset_code_deps()
            )
            password_router.add_api_route(
                "/change", change_password, methods=["POST"],
                response_model=StatusResponse,
                dependencies=limiter_deps.get_request_reset_code_deps()
            )
            password_router.add_api_route(
                "/verify_token", verify_token, methods=["POST"],
                response_model=StatusResponse,
                dependencies=limiter_deps.get_request_reset_code_deps()
            )
            password_router.add_api_route(
                "/reset", reset_password, methods=["POST"],
                response_model=StatusResponse,
                dependencies=limiter_deps.get_request_reset_code_deps()
            )

        if self.router_config.ENABLE_ADMIN_PANEL:
            from .routes.admin import register_new_user

            admin_router = APIRouter(prefix="/admin", tags=["auth"])
            self.include_router(admin_router)
            # Admin routes
            admin_router.add_api_route(
                "/register_user",
                endpoint=register_new_user,
                methods=["POST"],
                response_model=StatusResponse,
            )
