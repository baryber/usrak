from typing import Optional

from fastapi import HTTPException


class MailSendRateLimitException(HTTPException):
    def __init__(self, wait_time: int):
        super().__init__(
            status_code=429,
            detail="Too Many Requests",
            headers={"Retry-After": str(wait_time)},
        )


class RedisOperationFailedException:
    def __init__(self):
        super().__init__(
            status_code=500,
            detail="Internal server error",
        )
