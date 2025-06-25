from enum import Enum


class AuthProvider(Enum):
    EMAIL = 'email'
    GOOGLE = 'google'
    TELEGRAM = 'telegram'


class RateLimiterObjectType(Enum):
    CODE = "code"
    LINK = "link"


class ResponseNextStep(Enum):
    SIGNUP = "signup"
    VERIFY = "verify"
    LOGIN = "login"
    RESET_PASSWORD = "reset_password"
    CHANGE_PASSWORD = "change_password"
    CHANGE_EMAIL = "change_email"
    LOGOUT = "logout"
    WAIT_FOR_VERIFICATION = "wait_for_verification"


class TokenTypes(Enum):
    ACCESS = "access_token"
    REFRESH = "refresh_token"
    SIGNUP_VERIFY = "signup_verify_token"
    PASSWORD_RESET = "password_reset_token"
