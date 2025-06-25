from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional

from usrak.core.schemas.security import SecretContext

T = TypeVar("T")


class OneTimeVerificationABS(Generic[T], ABC):
    def __init__(self, prefix: str):
        self.prefix = prefix

    @abstractmethod
    async def create_secret(
            self,
            user_identifier: str,
            secret_context: Optional[SecretContext] = None
    ) -> T | None:
        raise NotImplementedError

    @abstractmethod
    async def verify_secret(
            self,
            secret: T,
            user_identifier: str,
            secret_context: Optional[SecretContext] = None
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_create_attempt_wait_time(
            self,
            user_identifier: str
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def cleanup_secrets(
            self,
            user_identifier: str
    ) -> None:
        raise NotImplementedError
