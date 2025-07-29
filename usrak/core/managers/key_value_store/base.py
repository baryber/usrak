from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

from fastapi import Depends

from usrak.core.dependencies.config_provider import get_app_config, get_router_config


if TYPE_CHECKING:
    from usrak.core.config_schemas import AppConfig, RouterConfig


class SingletonABCMeta(ABCMeta):
    """
    Метакласс, совмещающий Singleton и ABC.
    При первом создании экземпляра сохраняет его,
    при последующих — возвращает сохранённый.
    """
    _instances: dict[type, object] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class KeyValueStoreABS(metaclass=SingletonABCMeta):
    """Хранилище ключ-значение."""

    _app_config: "AppConfig" = None
    _router_config: "RouterConfig" = None

    def __init__(
            self,
            app_config: "AppConfig",  # For FastAPI type checking
            router_config: "RouterConfig"  # For FastAPI type checking
    ):
        self._app_config = app_config
        self._router_config = router_config

    @property
    def app_config(self) -> "AppConfig":
        if self._app_config is None:
            raise RuntimeError("AppConfig is not set yet.")
        return self._app_config

    @property
    def router_config(self) -> "RouterConfig":
        if self._router_config is None:
            raise RuntimeError("RouterConfig is not set yet.")
        return self._router_config

    @abstractmethod
    async def set(self, key: str, value: str, ttl: int | float = None) -> None:
        """Добавляет (обновляет) значение в хранилище по ключу."""
        raise NotImplementedError

    @abstractmethod
    async def get(self, key: str) -> str | None:
        """Получает значение из хранилища по ключу."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Удаляет значение из хранилища по ключу."""
        raise NotImplementedError

    @abstractmethod
    async def expire(self, key: str, ttl: float) -> bool:
        """Устанавливает время жизни ключа в секундах."""
        raise NotImplementedError

    @abstractmethod
    async def alive(self) -> bool:
        """Доступен ли хранилище."""
        raise NotImplementedError

    @abstractmethod
    async def ttl(self, key: str) -> int | float | None:
        """Сколько осталось времени жизни ключа в секундах."""
        raise NotImplementedError

    # --------- HASH ---------
    @abstractmethod
    async def hset(self, key: str, field: str, value: str) -> int:
        """
        Устанавливает поле hash-структуры.
        Возвращает 1, если поле новое, 0 если перезаписано.
        TTL нужно установить вручную на весь ключ.

        """
        raise NotImplementedError

    @abstractmethod
    async def hget(self, key: str, field: str) -> str | None:
        """Читает значение поля в hash-структуре."""
        raise NotImplementedError

    @abstractmethod
    async def hdel(self, key: str, *fields: str) -> int:
        """
        Удаляет одно или несколько полей из hash-структуры.
        Возвращает число удалённых полей.
        """
        raise NotImplementedError

    @abstractmethod
    async def hgetall(self, key: str) -> dict[str, str]:
        """Возвращает все поля и значения hash-структуры."""
        raise NotImplementedError

    @abstractmethod
    async def hexpire(self, key: str, ttl: float) -> bool:
        """Устанавливает TTL для hash-ключа."""
        raise NotImplementedError

    @abstractmethod
    async def httl(self, key: str) -> float | None:
        """Возвращает TTL hash-ключа или None."""
        raise NotImplementedError
