import pytest

from sqlmodel import SQLModel
from sqlmodel import Session, create_engine

from .user import TestUserModel
from .config import app_config


@pytest.fixture(scope="session")
def sync_engine(app_config):
    engine = create_engine(str(app_config.DATABASE_URL), echo=False)
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(sync_engine):
    # Для синхронных операций с БД, как в текущей реализации get_db
    # Важно: библиотека использует синхронный get_db, поэтому тесты тоже должны его использовать
    # или мокать get_db для использования асинхронной сессии, если бы библиотека была полностью async
    connection = sync_engine.connect()
    transaction = connection.begin()
    with Session(bind=connection) as session:

        yield session

        session.close()
        transaction.rollback()
        connection.close()
