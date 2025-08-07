import pytest
from httpx import AsyncClient
from fastapi import status

from usrak import AppConfig, RouterConfig
from tests.fixtures.user import TestUserModel, default_password, test_user, created_test_user
from sqlmodel import Session


@pytest.mark.asyncio
async def test_sign_in_success(
        client: AsyncClient,
        created_test_user: TestUserModel,  # Пользователь уже создан и активен/верифицирован по умолчанию в фикстуре
        default_password: str,
        app_config: AppConfig,  # для проверки кук
        router_config: RouterConfig,  # для проверки USER_MODEL
):
    """Тестирует успешный вход пользователя."""
    # Получаем сессию из контекста фикстуры client.app, если это необходимо для обновления пользователя
    # Однако, created_test_user уже сохранен в сессии db_session, которая используется приложением через override.
    # Поэтому прямое обновление объекта должно отразиться в БД.

    login_data = {
        "auth_provider": "email",
        "email": created_test_user.email,
        "password": default_password,
    }
    response = await client.post("/auth/sign-in", json=login_data)

    print(f"Response data: {response.json()}")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["success"] is True
    assert response_data["message"] == "Success login"

    # Проверка установки кук
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies

    access_token_cookie = response.cookies.get("access_token")
    # Проверка атрибутов куки, если они важны
    # Пример: assert access_token_cookie.httponly == app_config.COOKIE_HTTPONLY (если бы такое поле было)


@pytest.mark.asyncio
async def test_sign_in_invalid_credentials_wrong_password(
        client: AsyncClient,
        created_test_user: TestUserModel
):
    """Тестирует вход с неверным паролем."""

    login_data = {
        "auth_provider": "email",
        "email": created_test_user.email,
        "password": "wrongpassword",
    }
    response = await client.post("/auth/sign-in", json=login_data)
    assert response.status_code == status.HTTP_403_FORBIDDEN  # InvalidCredentialsException
    response_data = response.json()
    assert response_data["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_sign_in_user_not_found(client: AsyncClient):
    """Тестирует вход несуществующего пользователя."""
    login_data = {
        "auth_provider": "email",
        "email": "nonexistent@example.com",
        "password": "somepassword",
    }
    response = await client.post("/auth/sign-in", json=login_data)
    assert response.status_code == status.HTTP_403_FORBIDDEN  # InvalidCredentialsException
    response_data = response.json()
    assert response_data["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_sign_in_user_not_verified(
        client: AsyncClient,
        unverified_user: TestUserModel,
        default_password: str
):
    """Тестирует вход неверифицированного пользователя."""

    login_data = {
        "auth_provider": "email",
        "email": unverified_user.email,
        "password": default_password,
    }
    response = await client.post("/auth/sign-in", json=login_data)
    assert response.status_code == status.HTTP_403_FORBIDDEN  # UserNotVerifiedException
    response_data = response.json()
    assert response_data["detail"] == "Not verified"


@pytest.mark.asyncio
async def test_sign_in_user_not_active(
        client: AsyncClient,
        inactive_user: TestUserModel,
        default_password: str
):
    """Тестирует вход неактивного пользователя."""

    login_data = {
        "auth_provider": "email",
        "email": inactive_user.email,
        "password": default_password,
    }
    response = await client.post("/auth/sign-in", json=login_data)
    assert response.status_code == status.HTTP_403_FORBIDDEN  # UserDeactivatedException
    response_data = response.json()
    assert response_data["detail"] == "User deactivated"


@pytest.mark.asyncio
async def test_sign_in_auth_provider_mismatch(
        client: AsyncClient,
        created_test_user: TestUserModel,  # auth_provider='email' по умолчанию в фикстуре
        default_password: str,
        db_session: Session
):
    """Тестирует вход с несоответствием провайдера аутентификации."""

    # created_test_user.auth_provider уже 'email'
    db_session.add(created_test_user)
    db_session.commit()

    login_data = {
        "auth_provider": "google",  # Пытаемся войти через google с email/password
        "email": created_test_user.email,
        "password": default_password,
    }
    # Ожидаем ошибку валидации схемы UserLogin, т.к. google не предполагает password
    # или ошибку AuthProviderMismatchException, если валидация пройдет, но логика в руте отловит.
    # Судя по схеме UserLogin, auth_provider может быть только "email".
    # Значит, будет ошибка валидации 422.
    response = await client.post("/auth/sign-in", json=login_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_check_auth_authenticated(
        client: AsyncClient,
        created_test_user: TestUserModel,
        default_password: str
):
    """Тестирует /check_auth для аутентифицированного пользователя."""

    login_data = {
        "auth_provider": "email",
        "email": created_test_user.email,
        "password": default_password
    }
    response = await client.post("/auth/sign-in", json=login_data)  # Логинимся для получения кук
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["success"] is True

    print(f"\nCookies: {client.cookies}")

    response = await client.post("/auth/check-auth")

    print(f"Response data: {response.json()}")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["success"] is True
    assert response_data["data"]["is_authenticated"] is True


@pytest.mark.asyncio
async def test_check_auth_unauthenticated(client: AsyncClient):
    """Тестирует /check_auth для неаутентифицированного пользователя."""
    response = await client.post("/auth/check-auth")
    # Ожидаем ошибку, так как get_user_if_verified_and_active вызовет UnauthorizedException
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_user_profile_authenticated(
        client: AsyncClient,
        created_test_user: TestUserModel,
        default_password: str
):
    """Тестирует /profile для аутентифицированного пользователя."""
    created_test_user.is_active = True
    created_test_user.is_verified = True

    login_data = {"auth_provider": "email", "email": created_test_user.email, "password": default_password}
    login_resp = await client.post("/auth/sign-in", json=login_data)
    assert login_resp.status_code == status.HTTP_200_OK

    response = await client.get("/auth/profile")
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["success"] is True
    assert response_data["data"]["mail"] == created_test_user.email
    assert response_data["data"]["user_name"] == created_test_user.user_name  # Может быть None
    assert response_data["data"]["user_id"] == created_test_user.external_id  # Может быть None


@pytest.mark.asyncio
async def test_user_profile_unauthenticated(client: AsyncClient):
    """Тестирует /profile для неаутентифицированного пользователя."""
    response = await client.get("/auth/profile")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_logout_success(
        client: AsyncClient,
        created_test_user: TestUserModel,
        default_password: str
):
    """Тестирует успешный выход пользователя."""
    created_test_user.is_active = True
    created_test_user.is_verified = True

    login_data = {"auth_provider": "email", "email": created_test_user.email, "password": default_password}
    login_response = await client.post("/auth/sign-in", json=login_data)
    assert "access_token" in login_response.cookies

    logout_response = await client.post("/auth/logout")
    assert logout_response.status_code == status.HTTP_200_OK
    response_data = logout_response.json()
    # В logout.py используется `status=True`, а в `StatusResponse` поле `success`.
    assert response_data["success"] is True
    assert response_data["message"] == "Operation completed"

    # Проверяем, что куки удалены (max-age=0 или expires в прошлом)
    # httpx не предоставляет легкого способа проверить это прямо,
    # но мы можем проверить, что заголовок set-cookie для удаления был отправлен.
    # Более надежно - проверить, что последующий запрос с этими куками (если бы клиент их сохранил) не работает.
    # Или проверить, что в logout_response.cookies куки имеют атрибуты удаления.
    # Например, httpx сохраняет куки в client.cookies.
    # После logout, client.cookies должны быть очищены или помечены как истекшие.

    # Проверим, что куки действительно удалены из сессии клиента httpx
    assert client.cookies.get("access_token") is None
    assert client.cookies.get("refresh_token") is None

    # И что в ответе были команды на удаление кук
    # set_cookie_headers = logout_response.headers.getlist('set-cookie')
    # assert any('access_token=;' in h or 'access_token="";' in h for h in set_cookie_headers)
    # assert any('refresh_token=;' in h or 'refresh_token="";' in h for h in set_cookie_headers)
    # Точная проверка заголовков set-cookie для удаления может быть сложной из-за форматов даты/max-age.
    # Проверка отсутствия кук в клиенте после запроса - хороший индикатор.

    # Проверим, что последующий запрос к защищенному эндпоинту не проходит
    check_auth_resp = await client.post("/auth/check-auth")
    assert check_auth_resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_refresh_token_success(
        client: AsyncClient,
        created_test_user: TestUserModel,
        default_password: str,
        app_config: AppConfig
):
    """Тестирует успешное обновление токенов."""
    created_test_user.is_active = True
    created_test_user.is_verified = True

    login_data = {"auth_provider": "email", "email": created_test_user.email, "password": default_password}
    login_response = await client.post("/auth/sign-in", json=login_data)
    assert login_response.status_code == status.HTTP_200_OK

    original_access_token = client.cookies.get("access_token")
    original_refresh_token = client.cookies.get("refresh_token")
    assert original_access_token
    assert original_refresh_token

    # Для теста может потребоваться "прокрутить" время или убедиться, что KVS работает корректно
    # В данном случае, мы просто вызываем refresh.
    refresh_response = await client.post("/auth/refresh")
    assert refresh_response.status_code == status.HTTP_200_OK
    response_data = refresh_response.json()
    assert response_data["success"] is True

    new_access_token = client.cookies.get("access_token")
    new_refresh_token = client.cookies.get("refresh_token")

    assert new_access_token
    assert new_refresh_token
    assert new_access_token != original_access_token
    assert new_refresh_token != original_refresh_token  # AuthTokensManager должен генерировать новый refresh токен

    # Проверим, что новый access_token работает
    profile_response = await client.get("/auth/profile")
    assert profile_response.status_code == status.HTTP_200_OK
    profile_data = profile_response.json()
    assert profile_data["data"]["mail"] == created_test_user.email


@pytest.mark.asyncio
async def test_refresh_token_no_refresh_cookie(
        client: AsyncClient,
        created_test_user: TestUserModel,
        default_password: str
):
    """Тестирует обновление токенов при отсутствии refresh_token куки."""
    created_test_user.is_active = True
    created_test_user.is_verified = True

    login_data = {"auth_provider": "email", "email": created_test_user.email, "password": default_password}
    await client.post("/auth/sign-in", json=login_data)

    client.cookies.delete("refresh_token")  # Удаляем куку

    response = await client.post("/auth/refresh")
    # get_user_if_verified_and_active -> get_user -> decode_jwt_token(access_token) -> OK
    # Но в refresh.py есть `if not refresh_token or not access_token: raise exc.UnauthorizedException`
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_refresh_token_no_access_cookie(
        client: AsyncClient,
        created_test_user: TestUserModel,
        default_password: str
):
    """Тестирует обновление токенов при отсутствии access_token куки."""
    created_test_user.is_active = True
    created_test_user.is_verified = True

    login_data = {"auth_provider": "email", "email": created_test_user.email, "password": default_password}
    await client.post("/auth/sign-in", json=login_data)

    client.cookies.delete("access_token")  # Удаляем куку

    response = await client.post("/auth/refresh")
    # get_user_if_verified_and_active -> get_user -> access_token is None -> UnauthorizedException
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_refresh_token_invalid_refresh_token_in_kvs(
        client: AsyncClient,
        created_test_user: TestUserModel,
        default_password: str,
        app_config: AppConfig,
        router_config: RouterConfig  # Для доступа к KVS через auth_tokens_manager
):
    """
    Тестирует обновление токенов, если refresh_token в KVS не совпадает (например, сессия была перехвачена).
    Это сложный сценарий для прямого теста без глубокого мока KVS или AuthTokensManager.
    AuthTokensManager.handle_refresh_token должен отлавливать это.
    В текущей реализации AuthTokensManager (usrak.core.managers.tokens.auth)
    `await self.deactivate_token` перед созданием нового, что по сути инвалидирует старый JTI.
    Если JTI не совпадет при `validate_token`, то будет ошибка.
    """
    pytest.skip("TODO: Требуется более глубокое мокирование KVS или AuthTokensManager "
                "для имитации невалидного токена в KVS")
    # TODO: Реализовать тест, который проверяет ситуацию, когда refresh_token в KVS не совпадает с ожидаемым.
    # Примерная логика:
    # 1. Логинимся, получаем токены.
    # 2. Вручную меняем JTI для refresh_token в KVS (или удаляем его).
    # 3. Пытаемся сделать refresh.
    # 4. Ожидаем ошибку UnauthorizedException.

    # created_test_user.is_active = True
    # created_test_user.is_verified = True
    # login_data = {"auth_provider": "email", "email": created_test_user.email, "password": default_password}
    # await client.post("/auth/sign-in", json=login_data)

    # auth_tokens_manager = router_config.AUTH_MANAGER_CLASS() # Предполагая, что такая фикстура или способ есть
    # kvs = auth_tokens_manager.kvs
    # refresh_token_key_in_kvs = f"{auth_tokens_manager.JTI_PREFIX}:{auth_tokens_manager.REFRESH_TOKEN_PREFIX}:{created_test_user.internal_id}"
    # await kvs.hset(refresh_token_key_in_kvs, "0", "invalid_jti_value_for_test")

    # response = await client.post("/auth/refresh")
    # assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_refresh_token_user_deactivated_after_login(
        client: AsyncClient,
        created_test_user: TestUserModel,
        default_password: str,
        db_session: Session
):
    """Тестирует refresh, если пользователь был деактивирован после получения токенов."""
    created_test_user.is_active = True
    created_test_user.is_verified = True
    login_data = {"auth_provider": "email", "email": created_test_user.email, "password": default_password}
    await client.post("/auth/sign-in", json=login_data)

    # Деактивируем пользователя в БД
    user_in_db = db_session.get(TestUserModel, created_test_user.id)
    assert user_in_db is not None
    user_in_db.is_active = False  # type: ignore
    db_session.add(user_in_db)
    db_session.commit()

    response = await client.post("/auth/refresh")
    # get_user_if_verified_and_active должен выбросить UserDeactivatedException
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "User deactivated"
