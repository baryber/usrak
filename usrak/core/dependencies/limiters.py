from fastapi import Depends
from usrak.core import limiter_identifiers as identifiers
from usrak.core.dependencies.config_provider import get_app_config, get_router_config

__all__ = [
    "get_login_deps",
    "get_signup_deps",
    "get_logout_deps",
    "get_refresh_token_deps",
    "get_reset_password_deps",
    "get_request_reset_code_deps",
    "get_request_signup_code_deps",
    "get_verify_signup_deps",
    "get_oauth_deps",
]


def _build_deps(times: int, seconds: int, identifier) -> list:
    """
    Internal helper: build a dependency list for a rate limiter.
    """
    deps = []
    router_config = get_router_config()
    if router_config.USE_REDIS_FOR_RATE_LIMITING:
        from fastapi_limiter.depends import RateLimiter

        deps.append(
            Depends(
                RateLimiter(
                    times=times,
                    seconds=seconds,
                    identifier=identifier,
                )
            )
        )
    return deps


def get_login_deps() -> list:
    app_config = get_app_config()
    return _build_deps(
        times=app_config.LOGIN_RATE_LIMIT_TIMES,
        seconds=app_config.LOGIN_RATE_LIMIT_SECONDS,
        identifier=identifiers.login_rate_identifier,
    )


def get_signup_deps() -> list:
    app_config = get_app_config()
    return _build_deps(
        times=app_config.SIGNUP_RATE_LIMIT_TIMES,
        seconds=app_config.SIGNUP_RATE_LIMIT_SECONDS,
        identifier=identifiers.signup_rate_identifier,
    )


def get_logout_deps() -> list:
    app_config = get_app_config()
    return _build_deps(
        times=app_config.LOGOUT_RATE_LIMIT_TIMES,
        seconds=app_config.LOGOUT_RATE_LIMIT_SECONDS,
        identifier=identifiers.logout_rate_identifier,
    )


def get_refresh_token_deps() -> list:
    app_config = get_app_config()
    return _build_deps(
        times=app_config.REFRESH_TOKEN_RATE_LIMIT_TIMES,
        seconds=app_config.REFRESH_TOKEN_RATE_LIMIT_SECONDS,
        identifier=identifiers.refresh_rate_identifier,
    )


def get_reset_password_deps() -> list:
    app_config = get_app_config()
    return _build_deps(
        times=app_config.RESET_PASSWORD_RATE_LIMIT_TIMES,
        seconds=app_config.RESET_PASSWORD_RATE_LIMIT_SECONDS,
        identifier=identifiers.reset_password_rate_identifier,
    )


def get_request_reset_code_deps() -> list:
    app_config = get_app_config()
    return _build_deps(
        times=app_config.REQUEST_RESET_CODE_RATE_LIMIT_TIMES,
        seconds=app_config.REQUEST_RESET_CODE_RATE_LIMIT_SECONDS,
        identifier=identifiers.request_reset_code_rate_identifier,
    )


def get_request_signup_code_deps() -> list:
    app_config = get_app_config()
    return _build_deps(
        times=app_config.REQUEST_SIGNUP_CODE_RATE_LIMIT_TIMES,
        seconds=app_config.REQUEST_SIGNUP_CODE_RATE_LIMIT_SECONDS,
        identifier=identifiers.request_signup_code_rate_identifier,
    )


def get_verify_signup_deps() -> list:
    app_config = get_app_config()
    return _build_deps(
        times=app_config.VERIFY_SIGNUP_RATE_LIMIT_TIMES,
        seconds=app_config.VERIFY_SIGNUP_RATE_LIMIT_SECONDS,
        identifier=identifiers.verify_signup_rate_identifier,
    )


def get_oauth_deps() -> list:
    app_config = get_app_config()
    return _build_deps(
        times=app_config.OAUTH_RATE_LIMIT_TIMES,
        seconds=app_config.OAUTH_RATE_LIMIT_SECONDS,
        identifier=identifiers.oauth_rate_identifier,
    )
