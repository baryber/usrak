from typing import AsyncGenerator

import pytest

from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport


from usrak import AuthApp
from usrak.core.db import get_db

from .config import app_config, router_config
from .db import db_session


@pytest.fixture(scope="function")
async def app(
        app_config,
        router_config,
        db_session
) -> FastAPI:
    """
    Создает экземпляр AuthApp для тестов.
    """

    # Мокаем get_db, чтобы он возвращал нашу тестовую сессию
    # Это важно, так как get_db в библиотеке создает свою сессию
    def override_get_db():
        yield db_session

    # Создаем основной FastAPI app, в который будем монтировать AuthApp
    main_app = FastAPI()

    # Устанавливаем конфигурации в state основного приложения,
    # так как AuthApp будет их оттуда читать при монтировании.
    # Это имитирует то, как пользователь будет настраивать AuthApp.
    if not hasattr(main_app, "state"):
        from starlette.datastructures import State
        main_app.state = State()

    auth_extension = AuthApp(
        app_config=app_config,
        router_config=router_config,
    )

    # Переопределяем зависимость get_db внутри auth_extension
    auth_extension.dependency_overrides[get_db] = override_get_db

    main_app.mount("/auth", auth_extension)
    return main_app


@pytest.fixture(scope="function")
async def client(app: FastAPI) -> AsyncClient:
    async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver"
    ) as c:
        yield c
