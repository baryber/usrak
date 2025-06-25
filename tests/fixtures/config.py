import pytest

from usrak import AppConfig, RouterConfig

from .user import TestUserModel, TestUserReadSchema

TEST_DATABASE_URL = "postgresql://testusrak:testusrakpassword@localhost:15434/testusrakdb"
TEST_REDIS_URL = "redis://localhost:16379/0"


@pytest.fixture(scope="session")
def app_config() -> AppConfig:
    return AppConfig(
        DATABASE_URL=TEST_DATABASE_URL,
        REDIS_URL=TEST_REDIS_URL,  # Добавлено для полноты, если понадобится

        COOKIE_SECURE=False,  # Для тестов можно использовать небезопасные куки

        JWT_ACCESS_TOKEN_SECRET_KEY="test_access_secret",
        JWT_REFRESH_TOKEN_SECRET_KEY="test_refresh_secret",
        JWT_ONETIME_TOKEN_SECRET_KEY="test_onetime_secret",
        CODE_HASH_SALT="test_salt",
        FERNET_KEY="Y8RFpaIxSaAFNsB352tpLXl5znUw5anEKIZgclOezak=",  # Ключ должен быть 32 байта base64
        SMTP_SENDER_EMAIL="test@example.com",
        # Добавлено для LMDBKeyValueStore
        LMDB_PATH="./test_usrak_lmdb_data",  # Используем временный путь или путь в build артефактах
        LMDB_DEFAULT_TTL=3600,
        # Для тестов OAuth, если они будут выполняться без полного мока HTTPX
        GOOGLE_CLIENT_ID="test_google_client_id",
        GOOGLE_CLIENT_SECRET="test_google_client_secret",
        GOOGLE_REDIRECT_URI="http://testserver/auth/oauth/google/callback",
        TELEGRAM_AUTH_BOT_TOKEN="test_telegram_bot_token",
        REDIRECT_AFTER_AUTH_URL="http://testfrontend/after-auth"
    )


@pytest.fixture(scope="function")  # function scope для разных конфигураций роутера в тестах
def router_config(app_config) -> RouterConfig:
    return RouterConfig(
        USER_MODEL=TestUserModel,
        USER_READ_SCHEMA=TestUserReadSchema,
    )
