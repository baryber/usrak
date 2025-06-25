import time as pytime
import threading as th
from dataclasses import dataclass
from typing import Dict, Optional, TYPE_CHECKING

from .base import KeyValueStoreABS

if TYPE_CHECKING:
    from usrak.core.config_schemas import AppConfig, RouterConfig


@dataclass
class InMemoryValueObject:
    value: str
    expires_at: Optional[float] = None


@dataclass
class InMemoryHashObject:
    fields: Dict[str, str]
    expires_at: Optional[float] = None


class InMemoryKeyValueStore(KeyValueStoreABS):
    # TODO: Чтобы логика работало углубляться надо

    def __init__(
            self,
            app_config: "AppConfig",  # For FastAPI type checking
            router_config: "RouterConfig"  # For FastAPI type checking
    ):
        super().__init__(
            app_config=app_config,
            router_config=router_config
        )

        self._dict: Dict[str, InMemoryValueObject] = {}
        self._hashes: Dict[str, InMemoryHashObject] = {}
        self._lock = th.Lock()
        self._watcher_thread = th.Thread(target=self._expired_kv_pairs_watcher, daemon=True)
        self._watcher_thread.start()

    def _expired_kv_pairs_watcher(self):
        while True:
            now = pytime.time()
            with self._lock:
                # Очистка обычных ключей
                for key in list(self._dict.keys()):
                    if self._dict[key].expires_at is not None and now > self._dict[key].expires_at:
                        del self._dict[key]

                # Очистка hash-ключей
                for key in list(self._hashes.keys()):
                    if self._hashes[key].expires_at is not None and now > self._hashes[key].expires_at:
                        del self._hashes[key]

            pytime.sleep(1)

    async def set(self, key: str, value: str, ttl: int | float = None) -> None:
        expires_at = pytime.time() + ttl if ttl is not None else None
        with self._lock:
            self._dict[key] = InMemoryValueObject(value=value, expires_at=expires_at)

    async def get(self, key: str) -> str | None:
        with self._lock:
            item = self._dict.get(key)
            if item and (item.expires_at is None or pytime.time() <= item.expires_at):
                return item.value
            self._dict.pop(key, None)
            return None

    async def delete(self, key: str) -> None:
        with self._lock:
            self._dict.pop(key, None)

    async def expire(self, key: str, ttl: float) -> bool:
        with self._lock:
            if key in self._dict:
                self._dict[key].expires_at = pytime.time() + ttl
                return True
            return False

    async def ttl(self, key: str) -> int | float | None:
        with self._lock:
            item = self._dict.get(key)
            if item is None or item.expires_at is None:
                return None
            return max(0.0, item.expires_at - pytime.time())

    async def alive(self) -> bool:
        return True

    # -------- HASH ---------

    async def hset(self, key: str, field: str, value: str) -> int:
        with self._lock:
            created = 0
            if key not in self._hashes:
                self._hashes[key] = InMemoryHashObject(fields={})
                created = 1
            elif field not in self._hashes[key].fields:
                created = 1

            self._hashes[key].fields[field] = value
            return created

    async def hget(self, key: str, field: str) -> str | None:
        with self._lock:
            hash_obj = self._hashes.get(key)
            if hash_obj is None or (hash_obj.expires_at is not None and pytime.time() > hash_obj.expires_at):
                self._hashes.pop(key, None)
                return None
            return hash_obj.fields.get(field)

    async def hdel(self, key: str, *fields: str) -> int:
        with self._lock:
            hash_obj = self._hashes.get(key)
            if hash_obj is None:
                return 0
            removed = 0
            for field in fields:
                if field in hash_obj.fields:
                    del hash_obj.fields[field]
                    removed += 1
            if not hash_obj.fields:
                del self._hashes[key]
            return removed

    async def hgetall(self, key: str) -> dict[str, str]:
        with self._lock:
            hash_obj = self._hashes.get(key)
            if hash_obj is None or (hash_obj.expires_at is not None and pytime.time() > hash_obj.expires_at):
                self._hashes.pop(key, None)
                return {}
            return dict(hash_obj.fields)

    async def hexpire(self, key: str, ttl: float) -> bool:
        with self._lock:
            if key in self._hashes:
                self._hashes[key].expires_at = pytime.time() + ttl
                return True
            return False

    async def httl(self, key: str) -> float | None:
        with self._lock:
            hash_obj = self._hashes.get(key)
            if hash_obj is None or hash_obj.expires_at is None:
                return None
            return max(0.0, hash_obj.expires_at - pytime.time())
