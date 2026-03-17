from typing import Optional

import pytest

from sqlmodel import Field
from pydantic import BaseModel

from usrak import RoleModelBase, UserModelBase


class TestUserModel(UserModelBase, table=True):
    """Тестовая модель пользователя."""

    __test__ = False
    __tablename__ = "test_users"

    super_id: Optional[int] = Field(default=None, primary_key=True, index=True)

    extra_field: str | None = Field(default=None)


class TestRoleModel(RoleModelBase, table=True):
    """Тестовая модель роли."""

    __test__ = False
    __tablename__ = "test_roles"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)


class TestUserCreateSchema(BaseModel):
    """Тестовая схема для создания пользователей."""

    __test__ = False
    super_id: int | None = None
    email: str | None = None
    auth_provider: str = "email"
    is_active: bool = False
    is_verified: bool = False
    user_name: str | None = None
    extra_field: str | None = None
    password: str | None = Field()


class TestUserReadSchema(BaseModel):
    """Тестовая схема для чтения пользователей."""

    __test__ = False
    super_id: int | None = None
    email: str
    auth_provider: str
    is_active: bool
    is_verified: bool
    user_name: str | None = None
    extra_field: str | None = None

    model_config = {"from_attributes": True}


@pytest.fixture
def default_password() -> str:
    return "StrongPassword123"


@pytest.fixture
def default_email() -> str:
    return "testuser@example.com"


@pytest.fixture
def test_user(default_email, default_password) -> TestUserModel:
    from usrak.core.security import hash_password

    return TestUserModel(
        email=default_email,
        hashed_password=hash_password(default_password),
        auth_provider="email",
        is_active=True,
        is_verified=True,
    )


@pytest.fixture
async def created_test_user(
        db_session,
        test_user
) -> TestUserModel:
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)
    return test_user


@pytest.fixture
async def unverified_user(
        db_session,
        test_user
) -> TestUserModel:
    test_user.email = "unverified_" + test_user.email
    test_user.is_verified = False
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)
    return test_user


@pytest.fixture
async def inactive_user(
        db_session,
        test_user
) -> TestUserModel:
    test_user.email = "inactive_" + test_user.email
    test_user.is_active = False
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)
    return test_user
