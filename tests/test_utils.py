import pytest
from starlette.requests import Request
from starlette.datastructures import Headers

from usrak.utils.internal_id import generate_internal_id_from_str
from usrak.remote_address import get_remote_address
from usrak import AppConfig


def test_generate_internal_id_from_str():
    """Тестирует генерацию внутреннего ID."""
    internal_id = generate_internal_id_from_str()
    assert isinstance(internal_id, str)
    # Проверяем, что это валидный UUID (хотя функция просто вызывает uuid.uuid4())
    from uuid import UUID
    try:
        UUID(internal_id)
    except ValueError:
        pytest.fail("Generated internal_id is not a valid UUID string.")


@pytest.mark.asyncio
async def test_get_remote_address_direct_client(app_config: AppConfig):
    """Тестирует получение IP-адреса прямого клиента."""
    scope = {
        "type": "http",
        "client": ("1.2.3.4", 12345),
        "headers": Headers().raw,
        "app_config": app_config  # Для доступа к TRUSTED_PROXIES
    }
    # Модифицируем get_app_config, чтобы он возвращал тестовый app_config внутри get_remote_address
    # Это необходимо, так как get_remote_address вызывает get_app_config() глобально.
    # В реальном приложении FastAPI это будет работать через DI или middleware.
    # Для изолированного теста функции это нужно мокировать.
    original_get_app_config = None
    import usrak.remote_address
    try:
        # Подменяем глобальную функцию get_app_config
        original_get_app_config = usrak.remote_address.get_app_config
        usrak.remote_address.get_app_config = lambda: app_config

        request = Request(scope)
        assert get_remote_address(request) == "1.2.3.4"
    finally:
        if original_get_app_config:
            usrak.remote_address.get_app_config = original_get_app_config


@pytest.mark.asyncio
async def test_get_remote_address_with_x_forwarded_for_untrusted_proxy(app_config: AppConfig):
    """Тестирует X-Forwarded-For, когда непосредственный прокси не доверенный."""
    app_config.TRUSTED_PROXIES = ["192.168.1.1"]  # Доверенный только внутренний прокси
    scope = {
        "type": "http",
        "client": ("5.6.7.8", 54321),  # Этот прокси не в TRUSTED_PROXIES
        "headers": Headers({"X-Forwarded-For": "1.2.3.4, 10.0.0.1"}).raw,
        "app_config": app_config
    }
    original_get_app_config = None
    import usrak.remote_address
    try:
        original_get_app_config = usrak.remote_address.get_app_config
        usrak.remote_address.get_app_config = lambda: app_config

        request = Request(scope)
        # Так как 5.6.7.8 не доверенный, он и будет считаться клиентом
        assert get_remote_address(request) == "5.6.7.8"
    finally:
        if original_get_app_config:
            usrak.remote_address.get_app_config = original_get_app_config


@pytest.mark.asyncio
async def test_get_remote_address_with_x_forwarded_for_trusted_proxy(app_config: AppConfig):
    """Тестирует X-Forwarded-For, когда непосредственный прокси доверенный."""
    app_config.TRUSTED_PROXIES = ["127.0.0.1", "10.0.0.1"]  # Добавляем 10.0.0.1 в доверенные
    scope = {
        "type": "http",
        "client": ("10.0.0.1", 54321),  # Этот прокси доверенный
        "headers": Headers({"X-Forwarded-For": "1.2.3.4, 172.16.0.5"}).raw,
        # 1.2.3.4 - реальный IP, 172.16.0.5 - другой прокси
        "app_config": app_config
    }
    original_get_app_config = None
    import usrak.remote_address
    try:
        original_get_app_config = usrak.remote_address.get_app_config
        usrak.remote_address.get_app_config = lambda: app_config

        request = Request(scope)
        # 10.0.0.1 доверенный, смотрим X-Forwarded-For.
        # Последний не доверенный IP в X-Forwarded-For - это 172.16.0.5
        assert get_remote_address(request) == "172.16.0.5"
    finally:
        if original_get_app_config:
            usrak.remote_address.get_app_config = original_get_app_config


@pytest.mark.asyncio
async def test_get_remote_address_all_proxies_trusted(app_config: AppConfig):
    """Тестирует X-Forwarded-For, когда все прокси в цепочке доверенные."""
    app_config.TRUSTED_PROXIES = ["127.0.0.1", "10.0.0.1", "172.16.0.5"]
    scope = {
        "type": "http",
        "client": ("10.0.0.1", 54321),
        "headers": Headers({"X-Forwarded-For": "1.2.3.4, 172.16.0.5"}).raw,
        "app_config": app_config
    }
    original_get_app_config = None
    import usrak.remote_address
    try:
        original_get_app_config = usrak.remote_address.get_app_config
        usrak.remote_address.get_app_config = lambda: app_config

        request = Request(scope)
        # Все прокси доверенные, берется самый первый IP из X-Forwarded-For
        assert get_remote_address(request) == "1.2.3.4"
    finally:
        if original_get_app_config:
            usrak.remote_address.get_app_config = original_get_app_config


@pytest.mark.asyncio
async def test_get_remote_address_no_x_forwarded_for_header(app_config: AppConfig):
    """Тестирует случай отсутствия заголовка X-Forwarded-For."""
    scope = {
        "type": "http",
        "client": ("1.2.3.4", 12345),
        "headers": Headers().raw,  # Нет X-Forwarded-For
        "app_config": app_config
    }
    original_get_app_config = None
    import usrak.remote_address
    try:
        original_get_app_config = usrak.remote_address.get_app_config
        usrak.remote_address.get_app_config = lambda: app_config

        request = Request(scope)
        assert get_remote_address(request) == "1.2.3.4"
    finally:
        if original_get_app_config:
            usrak.remote_address.get_app_config = original_get_app_config


@pytest.mark.asyncio
async def test_get_remote_address_empty_x_forwarded_for(app_config: AppConfig):
    """Тестирует случай с пустым заголовком X-Forwarded-For."""
    scope = {
        "type": "http",
        "client": ("1.2.3.4", 12345),
        "headers": Headers({"X-Forwarded-For": ""}).raw,
        "app_config": app_config
    }
    original_get_app_config = None
    import usrak.remote_address
    try:
        original_get_app_config = usrak.remote_address.get_app_config
        usrak.remote_address.get_app_config = lambda: app_config

        request = Request(scope)
        assert get_remote_address(request) == "1.2.3.4"
    finally:
        if original_get_app_config:
            usrak.remote_address.get_app_config = original_get_app_config
