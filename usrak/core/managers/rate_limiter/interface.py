from typing import Optional, Callable, Any
from abc import ABC


class IFastApiRateLimiter(ABC):
    redis: Any
    prefix: Optional[str]
    lua_sha: Optional[str]
    identifier: Optional[Callable]
    http_callback: Optional[Callable]
    ws_callback: Optional[Callable]
    lua_script: str

    @classmethod
    async def init(
        cls,
        redis: Any,
        prefix: str = "fastapi-limiter",
        identifier: Optional[Callable] = ...,
        http_callback: Optional[Callable] = ...,
        ws_callback: Optional[Callable] = ...
    ) -> None:
        ...

    @classmethod
    async def close(cls) -> None:
        ...
