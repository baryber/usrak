from abc import ABC, abstractmethod
from typing import Tuple

from usrak.core.mixins import ConfigDependencyMixin


class Mail:
    receiver: str
    subject: str
    body: str


class SMTPClientABS(ABC, ConfigDependencyMixin):
    service_name: str
    connected: bool

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(cls).__new__(cls)
        return cls._instance

    def __init__(self, service_name: str = "Default SMTP") -> None:
        self.service_name = service_name
        self.connected = False

    @abstractmethod
    async def start(self) -> None:
        ...

    @abstractmethod
    async def stop(self) -> None:
        ...

    @abstractmethod
    async def send_mail(self, mail: Mail) -> Tuple[bool, str]:
        ...
