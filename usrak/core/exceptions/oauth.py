from fastapi import HTTPException


class NoCodeProvidedGoogleOauthException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=400,
            detail="Code not provided",
        )


class CodeExchangeErrorGoogleOauthException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=400,
            detail="Code exchange failed",
        )


class NoUserinfoReceivedGoogleOauthException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=400,
            detail="User info not received",
        )


class StateMismatchGoogleOauthException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=400,
            detail="State mismatch",
        )


class InvalidTelegramAuthException(HTTPException):
    def __init__(self, extra_detail: str = ""):
        super().__init__(
            status_code=403,
            detail="Invalid auth" + (": " + extra_detail if extra_detail else ""),
        )


class AuthProviderMismatchException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=400,
            detail="Provider mismatch",
        )


class UnsupportedAuthProvider(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=400,
            detail="Unsupported provider"
        )
