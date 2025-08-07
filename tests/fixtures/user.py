from typing import Optional

import pytest

from sqlmodel import Field
from pydantic import BaseModel
from pystructor import omit, pick

from usrak import UserModelBase


class TestUserModel(UserModelBase, table=True):
    """Тестовая модель пользователя."""

    __tablename__ = "test_users"

    super_id: Optional[int] = Field(default=None, primary_key=True, index=True)

    extra_field: str | None = Field(default=None)


@omit(TestUserModel, "hashed_password", "password_version", "external_id", "last_password_change")
class TestUserCreateSchema(BaseModel):
    """Тестовая схема для создания пользователей."""

    password: str | None = Field()


@pick(TestUserModel, "super_id", "email", "is_active", "is_verified", "user_name", "extra_field")
class TestUserReadSchema(BaseModel):
    """Тестовая схема для чтения пользователей."""

    class Config:
        from_attributes = True


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
