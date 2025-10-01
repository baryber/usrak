from typing import AsyncGenerator
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from .config_schemas import AppConfig
from .dependencies.config_provider import get_app_config


_ENGINES: dict[str, any] = {}
_SESSIONMAKERS: dict[str, async_sessionmaker[AsyncSession]] = {}


def get_async_engine(db_url: str):
    if db_url not in _ENGINES:
        engine = create_async_engine(db_url, echo=False, future=True)
        _ENGINES[db_url] = engine
        _SESSIONMAKERS[db_url] = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _SESSIONMAKERS[db_url]


async def get_db(
    config: AppConfig = Depends(get_app_config),
) -> AsyncGenerator[AsyncSession, None]:
    session_maker = get_async_engine(str(config.DATABASE_URL))
    async with session_maker() as session:
        yield session
