from fastapi import HTTPException


class UserAlreadyExistsException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=400,
            detail="User already exists",
        )


class UserDeactivatedException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=403,
            detail="User deactivated",
        )


class VerificationFailedException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=400,
            detail="Verification failed",
        )


class InvalidVerificationCodeException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=400,
            detail="Invalid verification code",
        )


class UserNotVerifiedException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=403,
            detail="Not verified",
        )


class PasswordChangeCoolDownException(HTTPException):
    def __init__(self, wait_time: int):
        super().__init__(
            status_code=400,
            detail=f"Too many password changes",
            headers={"Cool-Down": str(wait_time)}
        )


class AccessDeniedException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=403,
            detail="Access denied",
        )


class TooManyAPIKeysException(HTTPException):
    def __init__(self, max_keys: int):
        super().__init__(
            status_code=400,
            detail=f"Too many API keys, max is {max_keys}",
        )

