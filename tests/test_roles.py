from enum import Enum
import time

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from usrak import AuthApp, DefaultRoles, RouterConfig
from usrak.core import enums
from usrak.core.dependencies.role import require_roles
from usrak.core.dependencies.user import build_user_dependency
from usrak.core.db import get_db
from usrak.core.dependencies.config_provider import set_app_config, set_router_config
from usrak.core.managers.tokens.auth import AuthTokensManager
from usrak.core.schemas.security import JwtTokenPayloadData, SecretContext
from usrak.core.security import create_jwt_token, generate_jti, hash_password
from tests.fixtures.tokens import TestTokensModel, TestTokensReadSchema
from tests.fixtures.user import TestRoleModel, TestUserModel, TestUserReadSchema


class CustomRoles(str, Enum):
    ADMIN = "superuser"
    USER = "member"


class _FakeAuthTokensManager:
    async def validate_access_token(self, token: str, user_identifier: str, password_version: int | None) -> None:
        return None


class _AsyncSessionAdapter:
    def __init__(self, session):
        self._session = session

    async def exec(self, *args, **kwargs):
        return self._session.exec(*args, **kwargs)

    async def commit(self):
        self._session.commit()

    async def refresh(self, instance):
        self._session.refresh(instance)

    def add(self, instance):
        self._session.add(instance)

    def __getattr__(self, item):
        return getattr(self._session, item)


def _make_router_config(default_roles_enum=DefaultRoles) -> RouterConfig:
    return RouterConfig(
        USER_MODEL=TestUserModel,
        USER_READ_SCHEMA=TestUserReadSchema,
        USER_IDENTIFIER_FIELD_NAME="super_id",
        TOKENS_MODEL=TestTokensModel,
        TOKENS_READ_SCHEMA=TestTokensReadSchema,
        DEFAULT_ROLES_ENUM=default_roles_enum,
    )


def _build_access_token(app_config, user: TestUserModel) -> str:
    user_identifier = user.super_id
    assert user_identifier is not None
    payload = JwtTokenPayloadData(
        token_type="access_token",
        user_identifier=user_identifier,
        exp=int(time.time()) + 3600,
        jti=generate_jti(),
        secret_context=SecretContext(password_version=user.password_version, purpose="login"),
    )
    return create_jwt_token(payload, app_config.JWT_ACCESS_TOKEN_SECRET_KEY)


def _build_auth_app(app_config, router_config, db_session) -> FastAPI:
    auth_app = AuthApp(app_config=app_config, router_config=router_config)

    def override_get_db():
        yield _AsyncSessionAdapter(db_session)

    auth_app.dependency_overrides[get_db] = override_get_db
    auth_app.dependency_overrides[AuthTokensManager] = _FakeAuthTokensManager

    main_app = FastAPI()
    main_app.mount("/auth", auth_app)
    return main_app


@pytest.mark.asyncio
async def test_admin_register_user_allows_admin_role(
    app_config,
    db_session,
    default_password: str,
    monkeypatch,
):
    router_config = _make_router_config()
    monkeypatch.setattr("usrak.core.managers.sign_up.mail.gen_internal_id", lambda _email=None: 999)
    admin_user = TestUserModel(
        email="admin-role@example.com",
        hashed_password=hash_password(default_password),
        auth_provider="email",
        is_active=True,
        is_verified=True,
        role=DefaultRoles.ADMIN.value,
    )
    db_session.add(admin_user)
    db_session.commit()
    db_session.refresh(admin_user)

    app = _build_auth_app(app_config, router_config, db_session)
    access_token = _build_access_token(app_config, admin_user)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        client.cookies.set("access_token", access_token)
        response = await client.post(
            "/auth/admin/register_user",
            json={
                "auth_provider": "email",
                "email": "registered-by-admin@example.com",
                "password": "StrongPassword456",
            },
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_admin_register_user_rejects_non_admin_role(
    app_config,
    db_session,
    default_password: str,
    monkeypatch,
):
    router_config = _make_router_config()
    monkeypatch.setattr("usrak.core.managers.sign_up.mail.gen_internal_id", lambda _email=None: 999)
    plain_user = TestUserModel(
        email="plain-role@example.com",
        hashed_password=hash_password(default_password),
        auth_provider="email",
        is_active=True,
        is_verified=True,
        role=DefaultRoles.USER.value,
    )
    db_session.add(plain_user)
    db_session.commit()
    db_session.refresh(plain_user)

    app = _build_auth_app(app_config, router_config, db_session)
    access_token = _build_access_token(app_config, plain_user)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        client.cookies.set("access_token", access_token)
        response = await client.post(
            "/auth/admin/register_user",
            json={
                "auth_provider": "email",
                "email": "registered-by-user@example.com",
                "password": "StrongPassword456",
            },
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Access denied"


@pytest.mark.asyncio
async def test_require_roles_accepts_wildcard(app_config, db_session, default_password: str):
    router_config = _make_router_config()
    user = TestUserModel(
        email="wildcard-role@example.com",
        hashed_password=hash_password(default_password),
        auth_provider="email",
        is_active=True,
        is_verified=True,
        role=DefaultRoles.USER.value,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    set_app_config(app_config)
    set_router_config(router_config)

    access_token = _build_access_token(app_config, user)
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/protected",
            "headers": [(b"cookie", f"access_token={access_token}".encode())],
        }
    )

    dependency = require_roles("*")
    user = await dependency(
        connection=request,
        session=_AsyncSessionAdapter(db_session),
        app_config=app_config,
        router_config=router_config,
        tokens_manager=_FakeAuthTokensManager(),
    )

    assert user.email == "wildcard-role@example.com"


@pytest.mark.asyncio
async def test_require_roles_accepts_role_model_instance(app_config, db_session, default_password: str):
    router_config = _make_router_config()
    user = TestUserModel(
        email="moderator-role@example.com",
        hashed_password=hash_password(default_password),
        auth_provider="email",
        is_active=True,
        is_verified=True,
        role="moderator",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    set_app_config(app_config)
    set_router_config(router_config)

    moderator_role = TestRoleModel(name="moderator", description="Can access the route")

    access_token = _build_access_token(app_config, user)
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/protected",
            "headers": [(b"cookie", f"access_token={access_token}".encode())],
        }
    )

    dependency = require_roles(moderator_role)
    user = await dependency(
        connection=request,
        session=_AsyncSessionAdapter(db_session),
        app_config=app_config,
        router_config=router_config,
        tokens_manager=_FakeAuthTokensManager(),
    )

    assert user.email == "moderator-role@example.com"


@pytest.mark.asyncio
async def test_require_roles_accepts_multiple_roles(app_config, db_session, default_password: str):
    router_config = _make_router_config()
    user = TestUserModel(
        email="multi-role@example.com",
        hashed_password=hash_password(default_password),
        auth_provider="email",
        is_active=True,
        is_verified=True,
        role="moderator",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    set_app_config(app_config)
    set_router_config(router_config)

    access_token = _build_access_token(app_config, user)
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/protected",
            "headers": [(b"cookie", f"access_token={access_token}".encode())],
        }
    )

    dependency = require_roles("admin", "moderator")
    user = await dependency(
        connection=request,
        session=_AsyncSessionAdapter(db_session),
        app_config=app_config,
        router_config=router_config,
        tokens_manager=_FakeAuthTokensManager(),
    )

    assert user.email == "multi-role@example.com"


@pytest.mark.asyncio
async def test_build_user_dependency_optional_returns_none_for_inactive_user(
    app_config,
    db_session,
    default_password: str,
):
    router_config = _make_router_config()
    user = TestUserModel(
        email="inactive-optional@example.com",
        hashed_password=hash_password(default_password),
        auth_provider="email",
        is_active=False,
        is_verified=True,
        role=DefaultRoles.USER.value,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    set_app_config(app_config)
    set_router_config(router_config)

    access_token = _build_access_token(app_config, user)
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/protected",
            "headers": [(b"cookie", f"access_token={access_token}".encode())],
        }
    )

    dependency = build_user_dependency(optional=True, require_verified=True, require_active=True)
    resolved_user = await dependency(
        connection=request,
        session=_AsyncSessionAdapter(db_session),
        app_config=app_config,
        router_config=router_config,
        tokens_manager=_FakeAuthTokensManager(),
    )

    assert resolved_user is None


@pytest.mark.asyncio
async def test_build_user_dependency_keeps_access_cache_isolated_from_api_only(
    app_config,
    db_session,
    default_password: str,
):
    router_config = _make_router_config()
    user = TestUserModel(
        email="cache-isolated@example.com",
        hashed_password=hash_password(default_password),
        auth_provider="email",
        is_active=True,
        is_verified=True,
        role=DefaultRoles.USER.value,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    set_app_config(app_config)
    set_router_config(router_config)

    access_token = _build_access_token(app_config, user)
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/protected",
            "headers": [(b"cookie", f"access_token={access_token}".encode())],
        }
    )

    access_dependency = build_user_dependency(auth_mode=enums.AuthMode.ACCESS_ONLY)
    api_dependency = build_user_dependency(
        auth_mode=enums.AuthMode.API_ONLY,
        optional=True,
    )

    access_user = await access_dependency(
        connection=request,
        session=_AsyncSessionAdapter(db_session),
        app_config=app_config,
        router_config=router_config,
        tokens_manager=_FakeAuthTokensManager(),
    )
    api_user = await api_dependency(
        connection=request,
        session=_AsyncSessionAdapter(db_session),
        app_config=app_config,
        router_config=router_config,
        tokens_manager=_FakeAuthTokensManager(),
    )

    assert access_user.email == "cache-isolated@example.com"
    assert api_user is None


@pytest.mark.asyncio
async def test_admin_route_uses_overridden_default_roles_enum(
    app_config,
    db_session,
    default_password: str,
    monkeypatch,
):
    original_default_role = TestUserModel.__default_role__
    original_role_field_name = TestUserModel.__role_field_name__
    original_id_field_name = TestUserModel.__id_field_name__

    monkeypatch.setattr("usrak.core.managers.sign_up.mail.gen_internal_id", lambda _email=None: 999)
    router_config = _make_router_config(CustomRoles)

    admin_user = TestUserModel(
        email="custom-admin@example.com",
        hashed_password=hash_password(default_password),
        auth_provider="email",
        is_active=True,
        is_verified=True,
        role=CustomRoles.ADMIN.value,
    )
    db_session.add(admin_user)
    db_session.commit()
    db_session.refresh(admin_user)

    try:
        app = _build_auth_app(app_config, router_config, db_session)
        access_token = _build_access_token(app_config, admin_user)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            client.cookies.set("access_token", access_token)
            response = await client.post(
                "/auth/admin/register_user",
                json={
                    "auth_provider": "email",
                    "email": "registered-by-superuser@example.com",
                    "password": "StrongPassword456",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["success"] is True
    finally:
        TestUserModel.__default_role__ = original_default_role
        TestUserModel.__role_field_name__ = original_role_field_name
        TestUserModel.__id_field_name__ = original_id_field_name
