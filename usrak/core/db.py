from sqlmodel import create_engine, Session
from fastapi import Depends
from .config_schemas import AppConfig
from .dependencies.config_provider import get_app_config

_ENGINES = {}


def get_engine(db_url: str):
    if db_url not in _ENGINES:
        _ENGINES[db_url] = create_engine(db_url, echo=False)
    return _ENGINES[db_url]


def get_db(config: AppConfig = Depends(get_app_config)):
    # TODO: make it async
    engine = get_engine(str(config.DATABASE_URL))
    with Session(engine) as session:
        yield session
