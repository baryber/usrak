import os
import time
import json
import threading as th
from typing import TYPE_CHECKING

import lmdb
from usrak.core.logger import logger

from fastapi.concurrency import run_in_threadpool
from usrak.core.managers.key_value_store import KeyValueStoreABS

if TYPE_CHECKING:
    from usrak.core.config_schemas import AppConfig, RouterConfig


class LMDBKeyValueStore(KeyValueStoreABS):
    """
    LMDB-backed key-value store with separate namespaces for simple keys and hash-keys.

    Простые ключи: префикс 'k:'
    Hash-ключи: префикс 'h:'

    Хранит JSON-структуры под одним ключом, поддерживает TTL.
    """
    K_PREFIX = b"k:"
    H_PREFIX = b"h:"

    def __init__(
            self,
            app_config: "AppConfig",  # For FastAPI type checking
            router_config: "RouterConfig"  # For FastAPI type checking
    ):
        super().__init__(
            app_config=app_config,
            router_config=router_config
        )

        db_path = self.app_config.LMDB_PATH
        default_ttl = self.app_config.LMDB_DEFAULT_TTL

        if not os.path.exists(db_path):
            os.makedirs(db_path, exist_ok=True)
            logger.info(f"Created LMDB directory: {db_path}")

        if not isinstance(db_path, str):
            raise TypeError(f"LMDB path must be str: {db_path}")

        self.default_ttl = default_ttl
        self.env = lmdb.open(
            db_path,
            map_size=self.app_config.LMDB_MAP_SIZE,
            subdir=True,
            readonly=False,
            max_dbs=1,
            lock=True,
            readahead=True,
            max_readers=512
        )
        self._watcher_thread = th.Thread(
            target=self._expired_kv_pairs_watcher,
            args=(self.app_config.LMDB_CLEANUP_INTERVAL,),
            daemon=True,
        )
        self._watcher_thread.start()

    def _expired_kv_pairs_watcher(self, interval: int):
        while True:
            try:
                with self.env.begin(write=True) as txn:
                    now = time.time()
                    for raw_key, raw_val in txn.cursor():
                        try:
                            data = json.loads(raw_val.decode())
                            exp = data.get("exp")
                            if exp is not None and now > exp:
                                txn.delete(raw_key)
                                logger.debug(f"Expired: {raw_key} deleted")
                        except Exception:
                            continue
            except Exception as e:
                logger.error(f"[TTL Watcher] {e}")
            time.sleep(interval)

    async def alive(self) -> bool:
        return await run_in_threadpool(self.__alive_sync)

    def __alive_sync(self) -> bool:
        try:
            with self.env.begin(write=False) as txn:
                txn.get(b'')
            return True

        except lmdb.Error:
            return False

    # -------- Асинхронные обёртки простых ключей --------
    async def set(self, key: str, value: str, ttl: float = None) -> None:
        await run_in_threadpool(self.__set_sync, key, value, ttl)

    async def get(self, key: str) -> str | None:
        return await run_in_threadpool(self.__get_sync, key)

    async def delete(self, key: str) -> None:
        """Удаляет только простой ключ, не затрагивая hash-namespace"""
        await run_in_threadpool(self.__delete_k_sync, key)

    async def expire(self, key: str, ttl: float) -> bool:
        """Устанавливает TTL для простого ключа"""
        return await run_in_threadpool(self.__expire_k_sync, key, ttl)

    async def ttl(self, key: str) -> float | None:
        """Возвращает TTL простого ключа или None"""
        return await run_in_threadpool(self.__ttl_k_sync, key)

    # -------- Асинхронные обёртки hash-namespace --------
    async def hset(self, key: str, field: str, value: str) -> int:
        return await run_in_threadpool(self.__hset_sync, key, field, value)

    async def hget(self, key: str, field: str) -> str | None:
        return await run_in_threadpool(self.__hget_sync, key, field)

    async def hdel(self, key: str, *fields: str) -> int:
        """Удаляет поля hash-ключа"""
        return await run_in_threadpool(self.__hdel_sync, key, *fields)

    async def hgetall(self, key: str) -> dict[str, str]:
        return await run_in_threadpool(self.__hgetall_sync, key)

    async def hexpire(self, key: str, ttl: float) -> bool:
        """Устанавливает TTL для hash-ключа"""
        return await run_in_threadpool(self.__expire_h_sync, key, ttl)

    async def httl(self, key: str) -> float | None:
        """Возвращает TTL hash-ключа или None"""
        return await run_in_threadpool(self.__ttl_h_sync, key)

    # -------- Синхронная логика простых ключей --------
    def __set_sync(self, key: str, value: str, ttl: float = None) -> None:
        with self.env.begin(write=True) as txn:
            data = {"v": value}
            if ttl is not None:
                data["exp"] = time.time() + ttl
            txn.put(self.K_PREFIX + key.encode(), json.dumps(data).encode())

    def __get_sync(self, key: str) -> str | None:
        raw = None
        with self.env.begin(write=False) as txn:
            raw = txn.get(self.K_PREFIX + key.encode())
        if not raw:
            return None
        data = json.loads(raw.decode())
        exp = data.get("exp")
        if exp is not None and time.time() > exp:
            self.__delete_k_sync(key)
            return None
        return data.get("v")

    def __delete_k_sync(self, key: str) -> None:
        with self.env.begin(write=True) as txn:
            txn.delete(self.K_PREFIX + key.encode())

    def __expire_k_sync(self, key: str, ttl: float) -> bool:
        with self.env.begin(write=True) as txn:
            raw = txn.get(self.K_PREFIX + key.encode())
            if not raw:
                return False
            data = json.loads(raw.decode())
            data["exp"] = time.time() + ttl
            txn.put(self.K_PREFIX + key.encode(), json.dumps(data).encode())
            return True

    def __ttl_k_sync(self, key: str) -> float | None:
        raw = None
        with self.env.begin(write=False) as txn:
            raw = txn.get(self.K_PREFIX + key.encode())
        if not raw:
            return None
        data = json.loads(raw.decode())
        exp = data.get("exp")
        return (exp - time.time()) if exp is not None else None

    # -------- Синхронная логика hash-namespace --------
    def __hset_sync(self, key: str, field: str, value: str) -> int:
        with self.env.begin(write=True) as txn:
            raw = txn.get(self.H_PREFIX + key.encode())
            now = time.time()
            if raw:
                data = json.loads(raw.decode())
                exp = data.get("exp")
                if exp is not None and now > exp:
                    data = {}
                    exp = None
                hmap = data.get("h", {})
            else:
                data = {}
                exp = None
                hmap = {}
            was_new = 1 if field not in hmap else 0
            hmap[field] = value
            if exp is None:
                exp = now + self.default_ttl
            new_data = {"h": hmap, "exp": exp}
            txn.put(self.H_PREFIX + key.encode(), json.dumps(new_data).encode())
            return was_new

    def __hget_sync(self, key: str, field: str) -> str | None:
        with self.env.begin(write=False) as txn:
            raw = txn.get(self.H_PREFIX + key.encode())
        if not raw:
            return None
        data = json.loads(raw.decode())
        exp = data.get("exp")
        if exp is not None and time.time() > exp:
            self.__delete_h_sync(key)
            return None
        return data.get("h", {}).get(field)

    def __hdel_sync(self, key: str, *fields: str) -> int:
        with self.env.begin(write=True) as txn:
            raw = txn.get(self.H_PREFIX + key.encode())
            if not raw:
                return 0
            data = json.loads(raw.decode())
            exp = data.get("exp")
            if exp is not None and time.time() > exp:
                txn.delete(self.H_PREFIX + key.encode())
                return 0
            hmap = data.get("h", {})
            removed = 0
            for f in fields:
                if f in hmap:
                    hmap.pop(f)
                    removed += 1
            if hmap:
                new_data = {"h": hmap, "exp": exp} if exp is not None else {"h": hmap}
                txn.put(self.H_PREFIX + key.encode(), json.dumps(new_data).encode())
            else:
                txn.delete(self.H_PREFIX + key.encode())
            return removed

    def __hgetall_sync(self, key: str) -> dict[str, str]:
        with self.env.begin(write=False) as txn:
            raw = txn.get(self.H_PREFIX + key.encode())
        if not raw:
            return {}
        data = json.loads(raw.decode())
        exp = data.get("exp")
        if exp is not None and time.time() > exp:
            self.__delete_h_sync(key)
            return {}
        return dict(data.get("h", {}))

    def __delete_h_sync(self, key: str) -> None:
        with self.env.begin(write=True) as txn:
            txn.delete(self.H_PREFIX + key.encode())

    def __expire_h_sync(self, key: str, ttl: float) -> bool:
        """Устанавливает TTL для hash-ключа"""
        with self.env.begin(write=True) as txn:
            raw = txn.get(self.H_PREFIX + key.encode())
            if not raw:
                return False
            data = json.loads(raw.decode())
            data["exp"] = time.time() + ttl
            txn.put(self.H_PREFIX + key.encode(), json.dumps(data).encode())
            return True

    def __ttl_h_sync(self, key: str) -> float | None:
        """Возвращает оставшийся TTL для hash-ключа или None"""
        with self.env.begin(write=False) as txn:
            raw = txn.get(self.H_PREFIX + key.encode())
        if not raw:
            return None
        data = json.loads(raw.decode())
        exp = data.get("exp")
        return (exp - time.time()) if exp is not None else None


if __name__ == '__main__':
    # Пример использования
    path = "./test.lmdb"
    store = LMDBKeyValueStore(db_path=str(path), map_size=2 ** 30, cleanup_interval=1)

    import asyncio


    async def test():
        await store.set("test", "value1", ttl=100)
        await store.hset("test", "key2", "value2")
        await store.hexpire("test", 200)

        print(await store.ttl("test"))
        print(await store.hgetall("test"))


    asyncio.run(test())
