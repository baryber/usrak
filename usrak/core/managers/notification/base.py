from abc import ABC, abstractmethod


class NotificationServiceABS(ABC):
    @abstractmethod
    async def send_signup_verification(self, email: str, token: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def send_password_reset_link(self, email: str, token: str) -> bool:
        raise NotImplementedError

    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...
