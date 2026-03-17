# UsrAK

[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-extension-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLModel](https://img.shields.io/badge/SQLModel-supported-7E57C2)](https://sqlmodel.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green)](./pyproject.toml)
[![Status](https://img.shields.io/badge/status-alpha-orange)](./pyproject.toml)
[![Version](https://img.shields.io/badge/version-0.3.0-blue)](./pyproject.toml)

Reusable authentication and authorization for FastAPI applications built on top of `FastAPI`, `SQLModel`, JWT cookies, and API tokens.

UsrAK is aimed at backend developers who want to plug a working auth surface into an existing FastAPI project without giving up control over models, schemas, or infrastructure choices.

## Table Of Contents

- [Why UsrAK](#why-usrak)
- [Features](#features)
- [Quick Start](#quick-start)
- [Built-In Routes](#built-in-routes)
- [How To Extend](#how-to-extend)
- [Project Layout](#project-layout)
- [Current Limitations](#current-limitations)
- [Development](#development)
- [Changelog](#changelog)

## Why UsrAK

- Bring auth into an existing FastAPI codebase instead of generating a whole starter app.
- Keep your own `SQLModel` tables and response schemas.
- Support cookie-based session auth and header-based API tokens in the same package.
- Toggle features per project with `AppConfig` and `RouterConfig`.
- Swap storage and delivery backends without rewriting routes.

## Features

| Capability | Status | Notes |
| --- | --- | --- |
| Email/password sign-in | Yes | Sets `access_token` and `refresh_token` cookies |
| Logout and token refresh | Yes | Cookie-based session flow |
| Current user/profile endpoint | Yes | Works with mounted auth app |
| Optional signup flow | Yes | Email registration can be enabled via config |
| Signup verification links | Yes | Driven by one-time tokens |
| Password reset via email | Yes | Link-based reset flow |
| API tokens | Yes | Includes create/list/delete endpoints |
| API token IP allowlist | Yes | `whitelisted_ip_addresses` on token model |
| Optional user resolution | Yes | Access cookie, API token, or both |
| Role-based protection | Yes | `require_roles(...)` dependency |
| Role-aware admin user management | Yes | Scoped `create/update/delete` checks by target role |
| Google OAuth | Yes | Redirect/callback flow |
| Telegram auth | Yes | Signed Telegram login payload |
| Admin user create/update/delete | Yes | Create, patch, and deactivate users behind policy checks |
| Pluggable KV store | Yes | In-memory, Redis, LMDB, or custom class |
| Pluggable notification service | Yes | No-op or SMTP-backed |
| Redis rate limiter backend | Not yet | Config surface exists, implementation is incomplete |

## Quick Start

### 1. Install

```bash
python -m pip install -e .[test]
```

Minimum runtime requirements from `pyproject.toml`:

- Python `>=3.10`
- `fastapi>=0.115.0`
- `sqlmodel>=0.0.24`

### 2. Define your models and read schemas

UsrAK is designed to work with your own SQLModel tables. You extend the provided abstract bases and point the router config at your concrete classes.

```python
from typing import Optional

from pydantic import BaseModel
from sqlmodel import Field

from usrak import RoleModelBase, TokensModelBase, UserModelBase


class User(UserModelBase, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)


class ApiToken(TokensModelBase, table=True):
    __tablename__ = "api_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)


class Role(RoleModelBase, table=True):
    __tablename__ = "roles"

    id: Optional[int] = Field(default=None, primary_key=True)


class UserRead(BaseModel):
    id: int | None = None
    email: str
    auth_provider: str
    is_active: bool
    is_verified: bool
    user_name: str | None = None

    model_config = {"from_attributes": True}


class ApiTokenRead(BaseModel):
    id: int | None = None
    token: str
    token_type: str
    name: str | None = None
    whitelisted_ip_addresses: list[str] | None = None
    is_deleted: bool
    expires_at: int | None = None

    model_config = {"from_attributes": True}
```

### 3. Configure the extension

```python
from usrak import AppConfig, RouterConfig

app_config = AppConfig(
    DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/app",
    REDIS_URL="redis://localhost:6379/0",
    JWT_ACCESS_TOKEN_SECRET_KEY="change-me",
    JWT_REFRESH_TOKEN_SECRET_KEY="change-me-too",
    JWT_ONETIME_TOKEN_SECRET_KEY="change-me-three",
    JWT_API_TOKEN_SECRET_KEY="change-me-four",
    CODE_HASH_SALT="change-me-five",
    FERNET_KEY="Y8RFpaIxSaAFNsB352tpLXl5znUw5anEKIZgclOezak=",
    COOKIE_SECURE=False,
    REDIRECT_AFTER_AUTH_URL="http://localhost:3000/auth/callback",
)

router_config = RouterConfig(
    USER_MODEL=User,
    USER_READ_SCHEMA=UserRead,
    ROLE_MODEL=Role,
    TOKENS_MODEL=ApiToken,
    TOKENS_READ_SCHEMA=ApiTokenRead,
    ENABLE_EMAIL_REGISTRATION=True,
    ENABLE_PASSWORD_RESET_VIA_EMAIL=True,
    USE_VERIFICATION_LINKS_FOR_SIGNUP=True,
    DEFAULT_USER_MANAGEMENT_RULES={
        "admin": {
            "create": {"user"},
            "update": {"user"},
            "delete": {"user"},
        }
    },
)
```

### 4. Mount `AuthApp`

```python
from fastapi import FastAPI
from usrak import AuthApp

app = FastAPI(title="My Product API")
auth_app = AuthApp(app_config=app_config, router_config=router_config)

app.mount("/auth", auth_app)
```

With that setup, the default auth routes are available under `/auth/...`, for example:

- `POST /auth/sign-in`
- `POST /auth/logout`
- `POST /auth/refresh`
- `GET /auth/profile`
- `POST /auth/check-auth`

Create your SQLModel tables and migrations separately. UsrAK does not create or migrate database schema for you.

### 5. Protect your own routes

UsrAK exposes dependencies for access-cookie auth, API-key auth, optional auth, and role checks.

```python
from fastapi import APIRouter, Depends

from usrak.core.dependencies.role import require_roles
from usrak.core.dependencies.user import get_user_access_only, get_user_api_only
from usrak.core.enums import DefaultRoles

router = APIRouter()


@router.get("/me")
async def get_me(user=Depends(get_user_access_only)):
    return {"email": user.email, "role": user.role}


@router.get("/service-token")
async def get_service_token_user(user=Depends(get_user_api_only)):
    return {"user_identifier": user.user_identifier}


@router.post("/admin-only")
async def admin_only(_admin=Depends(require_roles(DefaultRoles.ADMIN))):
    return {"ok": True}
```

For API-token authenticated requests, send the token in the `X-API-Key` header.

## Built-In Routes

Routes are enabled conditionally from `RouterConfig`.

| Route | Method | Purpose | Config flag |
| --- | --- | --- | --- |
| `/profile` | `GET` | Return current authenticated user profile | Always on |
| `/sign-in` | `POST` | Email/password login | Always on |
| `/logout` | `POST` | Clear auth cookies | Always on |
| `/check-auth` | `POST` | Verify current auth state | Always on |
| `/refresh` | `POST` | Rotate access/refresh cookies | Always on |
| `/api-tokens` | `GET` | List current user's API tokens | Always on |
| `/api-tokens` | `POST` | Create a new API token | Always on |
| `/api-tokens/{token_identifier}` | `DELETE` | Soft-delete API token | Always on |
| `/signup` | `POST` | Register by email | `ENABLE_EMAIL_REGISTRATION` |
| `/signup/send_link` | `POST` | Send signup verification link | `ENABLE_EMAIL_REGISTRATION` + `USE_VERIFICATION_LINKS_FOR_SIGNUP` |
| `/signup/verify` | `POST` | Verify signup token | `ENABLE_EMAIL_REGISTRATION` + `USE_VERIFICATION_LINKS_FOR_SIGNUP` |
| `/password/forgot` | `POST` | Start password reset | `ENABLE_PASSWORD_RESET_VIA_EMAIL` |
| `/password/change` | `POST` | Request password change flow | `ENABLE_PASSWORD_RESET_VIA_EMAIL` |
| `/password/verify_token` | `POST` | Verify password reset token | `ENABLE_PASSWORD_RESET_VIA_EMAIL` |
| `/password/reset` | `POST` | Complete password reset | `ENABLE_PASSWORD_RESET_VIA_EMAIL` |
| `/oauth/google` | `POST` | Start Google OAuth | `ENABLE_OAUTH` + `ENABLE_GOOGLE_OAUTH` |
| `/oauth/google/callback` | `GET` | Finish Google OAuth | `ENABLE_OAUTH` + `ENABLE_GOOGLE_OAUTH` |
| `/oauth/telegram` | `POST` | Telegram auth | `ENABLE_OAUTH` + `ENABLE_TELEGRAM_OAUTH` |
| `/admin/register_user` | `POST` | Create a user with explicit target role | `ENABLE_ADMIN_PANEL` |
| `/admin/users/{user_identifier}` | `PATCH` | Update user fields and optionally change role | `ENABLE_ADMIN_PANEL` |
| `/admin/users/{user_identifier}` | `DELETE` | Deactivate a user | `ENABLE_ADMIN_PANEL` |

## How To Extend

### Override model identity rules

If your primary key is not named `id`, point UsrAK at the correct field:

```python
router_config = RouterConfig(
    USER_MODEL=User,
    USER_READ_SCHEMA=UserRead,
    USER_IDENTIFIER_FIELD_NAME="external_pk",
    TOKENS_MODEL=ApiToken,
    TOKENS_READ_SCHEMA=ApiTokenRead,
    TOKENS_IDENTIFIER_FIELD_NAME="token_pk",
    TOKENS_OWNER_FIELD_NAME="owner_id",
    TOKENS_OWNER_RELATION_FIELD_NAME="owner",
)
```

This is one of the package's strongest extension points: it does not force a hardcoded internal user ID convention.

### Override roles and user-management rules

`RouterConfig.DEFAULT_ROLES_ENUM` lets you replace the default `admin/user` pair with your own string enum, as long as the enum still contains `ADMIN` and `USER`.

```python
from enum import Enum


class Roles(str, Enum):
    ADMIN = "superuser"
    USER = "member"
    AUDITOR = "auditor"
```

For admin user-management, `RouterConfig.DEFAULT_USER_MANAGEMENT_RULES` defines the default `create/update/delete`
matrix for roles from `DEFAULT_ROLES_ENUM`.

```python
router_config = RouterConfig(
    USER_MODEL=User,
    USER_READ_SCHEMA=UserRead,
    ROLE_MODEL=Role,
    TOKENS_MODEL=ApiToken,
    TOKENS_READ_SCHEMA=ApiTokenRead,
    DEFAULT_ROLES_ENUM=Roles,
    DEFAULT_USER_MANAGEMENT_RULES={
        "superuser": {
            "create": "*",
            "update": "*",
            "delete": "*",
        },
        "member": {
            "create": set(),
            "update": set(),
            "delete": set(),
        },
    },
)
```

If `ROLE_MODEL` is configured, per-role database overrides can refine the same policy at runtime through
`RoleModelBase.user_management_rules`.

```python
role = Role(
    name="manager",
    description="Can manage regular users",
    user_management_rules={
        "create": ["user"],
        "update": ["user"],
        "delete": ["user"],
    },
)
```

UsrAK resolves user-management permissions in this order:

- database override on the acting role, if present
- fallback to `DEFAULT_USER_MANAGEMENT_RULES`
- deny if no rule exists

### Swap infrastructure backends

UsrAK accepts either concrete classes or string shortcuts for several backends:

- `KEY_VALUE_STORE`: `"in_memory"`, `"redis"`, `"lmdb"`, or a custom `KeyValueStoreABS`
- `NOTIFICATION_SERVICE`: `"smtp"`, `"no_op"`, or a custom `NotificationServiceABS`
- `SMTP_CLIENT`: `"default"`, `"no_op"`, or a custom `SMTPClientABS`
- `FAST_API_RATE_LIMITER`: `"no_op"` today, custom implementation if you have one

The abstract interfaces live in:

- `usrak/core/managers/key_value_store/base.py`
- `usrak/core/managers/notification/base.py`
- `usrak/core/managers/rate_limiter/interface.py`
- `usrak/core/smtp/base.py`

### Add your own protected routers

The package is best treated as an auth module, not as the whole application. Mount it once, then build your product routes around its dependencies.

Good patterns:

- use `get_user_access_only` for browser/session routes
- use `get_user_api_only` for machine-to-machine calls
- use `get_optional_user_any` when auth should enrich, but not block, a request
- use `require_roles(...)` for admin or staff-only endpoints

Use admin user-management routes when you need target-role-aware checks.
Those routes enforce scoped policy for:

- `create`
- `update`
- `delete`

### Customize responses and schemas

UsrAK already wraps most responses in typed `CommonResponse` and `CommonDataResponse[...]` models. You control the user and token payload shapes by passing custom `USER_READ_SCHEMA` and `TOKENS_READ_SCHEMA`.

That means you can:

- keep internal DB fields private
- expose only public-safe attributes
- version your outward response contract without forking the auth logic

## Project Layout

```text
usrak/
  auth_app.py                  # FastAPI app wrapper
  auth_router.py               # Route registration
  core/
    config_schemas.py          # AppConfig and RouterConfig
    db.py                      # Async DB session factory
    dependencies/              # User, role, config, manager providers
    managers/                  # Tokens, signup, password reset, KV store, notification
    middleware/                # Request body and trusted proxy middleware
    models/                    # Base SQLModel classes
    schemas/                   # Request/response payloads
    security.py                # JWT, hashing, token helpers
  routes/                      # Feature routers
tests/
  fixtures/                    # Example models/config used by the test suite
```

## Current Limitations

- The project is still marked `Development Status :: 3 - Alpha`.
- `FAST_API_RATE_LIMITER="redis"` currently raises `NotImplementedError`.
- The package is PostgreSQL-first today:
  `AppConfig.DATABASE_URL` is typed as `PostgresDsn`, and `TokensModelBase` uses PostgreSQL `JSONB`.
- Admin `DELETE /auth/admin/users/{user_identifier}` currently performs controlled deactivation by setting
  `is_active=False`; it is not a hard delete.
- DB migrations are not managed by UsrAK. You own table creation, migrations, and lifecycle.
- Global config is stored in module-level state and several providers are cached with `lru_cache()`. Running multiple differently configured auth apps in the same process is risky.
- Parent config flags do not strictly enforce child flags.
  Example: passing `ENABLE_OAUTH=False` and `ENABLE_GOOGLE_OAUTH=True` still leaves Google OAuth enabled at the field level.
- OAuth support is currently focused on Google and Telegram only.
- Permission tables and `require_permissions(...)` are not implemented yet; authorization is currently centered on
  role checks and scoped user-management rules.
- Some implementation areas still contain debug prints and TODOs, so production hardening is not finished.

## Development

Run the usual checks before opening a PR:

```bash
python -m pytest
ruff check usrak tests
mypy usrak tests
```

Useful local targets:

```bash
python -m pytest -m "not docker_required"
python -m pytest tests/test_default_endpoints.py
```

For disposable infra during higher-level scenarios, use `docker-compose.tests.yaml`.

## Changelog

This section is derived from git tags and the current `HEAD`.

### 0.3.0 - 2026-03-16

Current `HEAD` version in `pyproject.toml` and not tagged yet in git.

- Added `RoleModelBase` to make role-based extension more explicit.
- Added role-aware admin user management with create, update, and deactivate flows.
- Added `ROLE_MODEL` and `DEFAULT_USER_MANAGEMENT_RULES` to support default and DB-driven policy resolution.
- Updated packaging metadata and project versioning.

### v0.2.3 - 2025-10-10

- Reworked common response schemas and response typing.
- Cleaned response-model structure around status/data payloads.

### v0.2.2 - 2025-10-02

- Added full API token management flow.
- Added API-token-specific dependencies and auth modes.
- Added `TOKENS_OWNER_RELATION_FIELD_NAME`.
- Added IP allowlists for API tokens with `whitelisted_ip_addresses`.
- Improved request handling by switching some auth resolution paths to `HTTPConnection`.
- Added secret-token creation helpers and token resolver improvements.

### v0.2.1 - 2025-08-13

- Added optional user dependency support via `get_optional_user`.

### v0.2.0 - 2025-08-07

- Removed the old `internal_id` assumption.
- Introduced dynamic user identification based on configurable model fields.

### v0.1.1 - 2025-07-29

- Fixed LMDB/KV-store caching behavior.
- Increased LMDB reader limits.
- Introduced singleton helpers around shared services.

### v0.1.0 - 2025-06-25

- Initial project foundation.

## License

MIT.
