from typing import Optional, Callable, Any
from usrak.core.managers.rate_limiter.interface import IFastApiRateLimiter


class NoOpFastApiRateLimiter(IFastApiRateLimiter):
    redis: Any = None
    prefix: Optional[str] = None
    lua_sha: Optional[str] = None
    identifier: Optional[Callable] = None
    http_callback: Optional[Callable] = None
    ws_callback: Optional[Callable] = None
    lua_script: str = "NOOP"

    @classmethod
    async def init(
        cls,
        redis: Any,
        prefix: str = "fastapi-limiter",
        identifier: Optional[Callable] = None,
        http_callback: Optional[Callable] = None,
        ws_callback: Optional[Callable] = None
    ) -> None:
        cls.redis = redis
        cls.prefix = prefix
        cls.identifier = identifier
        cls.http_callback = http_callback
        cls.ws_callback = ws_callback
        cls.lua_sha = "dummy-lua-sha"  # фиктивное значение

    @classmethod
    async def close(cls) -> None:
        # ничего не делаем
        pass

