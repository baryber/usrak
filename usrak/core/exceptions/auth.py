from fastapi import HTTPException


class InvalidCredentialsException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=403,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


class UnauthorizedException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidAccessTokenException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


class ExpiredAccessTokenException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=401,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidRefreshTokenException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidTokenException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
