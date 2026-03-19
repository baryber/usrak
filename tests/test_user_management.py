import time

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from usrak import AuthApp, DefaultRoles, RouterConfig
from usrak.core.db import get_db
from usrak.core.managers.tokens.auth import AuthTokensManager
from usrak.core.schemas.security import JwtTokenPayloadData, SecretContext
from usrak.core.security import create_jwt_token, generate_jti, hash_password
from tests.fixtures.tokens import TestTokensModel, TestTokensReadSchema
from tests.fixtures.user import TestRoleModel, TestUserModel, TestUserReadSchema


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


def _make_router_config() -> RouterConfig:
    return RouterConfig(
        USER_MODEL=TestUserModel,
        USER_READ_SCHEMA=TestUserReadSchema,
        USER_IDENTIFIER_FIELD_NAME="super_id",
        ROLE_MODEL=TestRoleModel,
        TOKENS_MODEL=TestTokensModel,
        TOKENS_READ_SCHEMA=TestTokensReadSchema,
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


def _create_user(db_session, email: str, role: str, password: str) -> TestUserModel:
    user = TestUserModel(
        email=email,
        hashed_password=hash_password(password),
        auth_provider="email",
        is_active=True,
        is_verified=True,
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _seed_role_rules(db_session) -> None:
    db_session.add_all(
        [
            TestRoleModel(
                name="superadmin",
                description="Can manage everyone",
                user_management_rules={"create": ["*"], "update": ["*"], "delete": ["*"]},
            ),
            TestRoleModel(
                name=DefaultRoles.ADMIN.value,
                description="Can manage staff and users",
                user_management_rules={
                    "create": ["admin", "manager", "user"],
                    "update": ["admin", "manager", "user"],
                    "delete": ["admin", "manager", "user"],
                },
            ),
            TestRoleModel(
                name="manager",
                description="Can manage only users",
                user_management_rules={
                    "create": ["user"],
                    "update": ["user"],
                    "delete": ["user"],
                },
            ),
            TestRoleModel(
                name=DefaultRoles.USER.value,
                description="Cannot manage anyone",
                user_management_rules={"create": [], "update": [], "delete": []},
            ),
        ]
    )
    db_session.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("actor_role", "target_role", "expected_status"),
    [
        ("superadmin", "admin", status.HTTP_200_OK),
        ("admin", "manager", status.HTTP_200_OK),
        ("manager", "user", status.HTTP_200_OK),
        ("manager", "admin", status.HTTP_403_FORBIDDEN),
        ("user", "user", status.HTTP_403_FORBIDDEN),
    ],
)
async def test_admin_role_matrix_for_create(
    app_config,
    db_session,
    default_password: str,
    monkeypatch,
    actor_role: str,
    target_role: str,
    expected_status: int,
):
    monkeypatch.setattr("usrak.core.managers.sign_up.mail.gen_internal_id", lambda _email=None: 999)
    router_config = _make_router_config()
    _seed_role_rules(db_session)
    actor = _create_user(
        db_session,
        email=f"{actor_role}@example.com",
        role=actor_role,
        password=default_password,
    )

    app = _build_auth_app(app_config, router_config, db_session)
    access_token = _build_access_token(app_config, actor)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        client.cookies.set("access_token", access_token)
        response = await client.post(
            "/auth/admin/register_user",
            json={
                "email": f"created-{actor_role}-{target_role}@example.com",
                "password": "StrongPassword456",
                "role": target_role,
            },
        )

    assert response.status_code == expected_status


@pytest.mark.asyncio
async def test_admin_role_matrix_rejects_unknown_target_role(
    app_config,
    db_session,
    default_password: str,
    monkeypatch,
):
    monkeypatch.setattr("usrak.core.managers.sign_up.mail.gen_internal_id", lambda _email=None: 999)
    router_config = _make_router_config()
    _seed_role_rules(db_session)
    actor = _create_user(db_session, email="superadmin@example.com", role="superadmin", password=default_password)

    app = _build_auth_app(app_config, router_config, db_session)
    access_token = _build_access_token(app_config, actor)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        client.cookies.set("access_token", access_token)
        response = await client.post(
            "/auth/admin/register_user",
            json={
                "email": "unknown-role@example.com",
                "password": "StrongPassword456",
                "role": "ghost",
            },
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json()["detail"] == "Invalid role: ghost"


@pytest.mark.asyncio
async def test_update_user_checks_current_and_new_role_permissions(
    app_config,
    db_session,
    default_password: str,
):
    router_config = _make_router_config()
    _seed_role_rules(db_session)
    actor = _create_user(db_session, email="manager@example.com", role="manager", password=default_password)
    target = _create_user(db_session, email="plain-user@example.com", role="user", password=default_password)

    app = _build_auth_app(app_config, router_config, db_session)
    access_token = _build_access_token(app_config, actor)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        client.cookies.set("access_token", access_token)
        allowed_response = await client.patch(
            f"/auth/admin/users/{target.super_id}",
            json={"user_name": "Managed User"},
        )
        denied_response = await client.patch(
            f"/auth/admin/users/{target.super_id}",
            json={"role": "admin"},
        )

    assert allowed_response.status_code == status.HTTP_200_OK
    assert allowed_response.json()["data"]["user_name"] == "Managed User"
    assert denied_response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_delete_user_deactivates_allowed_target(
    app_config,
    db_session,
    default_password: str,
):
    router_config = _make_router_config()
    _seed_role_rules(db_session)
    actor = _create_user(db_session, email="admin@example.com", role="admin", password=default_password)
    target = _create_user(db_session, email="delete-me@example.com", role="user", password=default_password)

    app = _build_auth_app(app_config, router_config, db_session)
    access_token = _build_access_token(app_config, actor)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        client.cookies.set("access_token", access_token)
        response = await client.delete(f"/auth/admin/users/{target.super_id}")

    db_session.refresh(target)
    assert response.status_code == status.HTTP_200_OK
    assert target.is_active is False


@pytest.mark.asyncio
async def test_delete_user_rejects_forbidden_target_role(
    app_config,
    db_session,
    default_password: str,
):
    router_config = _make_router_config()
    _seed_role_rules(db_session)
    actor = _create_user(db_session, email="manager@example.com", role="manager", password=default_password)
    target = _create_user(db_session, email="admin-target@example.com", role="admin", password=default_password)

    app = _build_auth_app(app_config, router_config, db_session)
    access_token = _build_access_token(app_config, actor)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        client.cookies.set("access_token", access_token)
        response = await client.delete(f"/auth/admin/users/{target.super_id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN
