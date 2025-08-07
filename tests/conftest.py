import asyncio

import pytest
from fakeredis import FakeAsyncRedis

from usrak.core.dependencies import config_provider


@pytest.fixture(scope="session")
def event_loop():
    """Overrides pytest-asyncio event_loop fixture to run in session scope."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


from .fixtures.user import TestUserModel, TestUserReadSchema  # noqa: E402
from .fixtures.user import default_email, default_password, test_user, created_test_user, unverified_user, inactive_user  # noqa: E402
from .fixtures.config import app_config, router_config, TEST_DATABASE_URL, TEST_REDIS_URL  # noqa: E402
from .fixtures.db import db_session, sync_engine  # noqa: E402
from .fixtures.app import app, client  # noqa: E402


@pytest.fixture(autouse=True)
def reset_extension_config_between_tests():
    """Сбрасывает глобальную конфигурацию расширения между тестами."""
    config_provider.app_config = None
    config_provider.router_config = None
    yield
    config_provider.app_config = None
    config_provider.router_config = None


@pytest.fixture(scope="function")
async def fake_redis_client() -> FakeAsyncRedis:
    """
    Предоставляет мок-клиент Redis для тестов.
    Использует fakeredis для имитации асинхронного клиента Redis.
    """
    # decode_responses=True важно, так как многие части кода ожидают строки, а не байты.
    client = FakeAsyncRedis(decode_responses=True)
    await client.flushdb()  # Очистка базы данных перед каждым тестом
    yield client
    await client.close()  # Закрытие соединения после теста
