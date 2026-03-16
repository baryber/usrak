import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from usrak import DefaultRoles
from usrak.core.models.role import RoleModelBase
from usrak.core.models.user import UserModelBase
from tests.fixtures.user import TestRoleModel, TestUserCreateSchema, TestUserModel


def test_user_model_base_cannot_be_instantiated():
    """Тестирует, что UserModelBase не может быть инстанциирован напрямую."""
    with pytest.raises(TypeError, match="UserModelBase is an abstract class and cannot be instantiated."):
        UserModelBase(super_id="test", email="test@example.com", auth_provider="email")


def test_role_model_base_cannot_be_instantiated():
    """Тестирует, что RoleModelBase не может быть инстанциирован напрямую."""
    with pytest.raises(TypeError, match="RoleModelBase is an abstract class and cannot be instantiated."):
        RoleModelBase(name="admin")


def test_test_role_model_creation():
    """Тестирует создание экземпляра TestRoleModel."""
    role = TestRoleModel(name="moderator", description="Can manage content")

    assert role.name == "moderator"
    assert role.description == "Can manage content"


def test_test_user_model_creation(db_session):  # db_session для потенциального сохранения
    """Тестирует создание экземпляра TestUserModel (наследника UserModelBase)."""
    original_id_field_name = TestUserModel.__id_field_name__
    TestUserModel.__id_field_name__ = "super_id"

    user_data = {
        "super_id": 123,
        "email": "test@example.com",
        "auth_provider": "email",
        "hashed_password": "hashed_pw",
        "extra_field": "extra_data"
    }
    user = TestUserModel(**user_data)

    try:
        assert user.user_identifier == 123
        assert user.email == "test@example.com"  # Нормализация должна произойти при валидации Pydantic
        assert user.auth_provider == "email"
        assert user.hashed_password == "hashed_pw"
        assert user.extra_field == "extra_data"
        assert user.is_verified is False  # Default
        assert user.is_active is False  # Default
        assert user.role == DefaultRoles.USER.value  # Default
        assert isinstance(user.signed_up_at, datetime)
        assert user.signed_up_at.tzinfo == timezone.utc
    finally:
        TestUserModel.__id_field_name__ = original_id_field_name


def test_user_model_email_normalization():
    """Тестирует нормализацию email в UserModelBase через TestUserModel."""
    user = TestUserModel(
        super_id=1,
        email=" TestUser@Example.COM ",
        auth_provider="email",
        hashed_password="hashed_pw"
    )
    assert user.email == "testuser@example.com"


def test_user_model_email_validation():
    """Тестирует валидацию email (Pydantic EmailStr)."""
    with pytest.raises(ValidationError):
        TestUserModel(
            super_id="user-invalid-email",
            email="notanemail",
            auth_provider="email"
        )


def test_user_model_defaults(db_session):
    pytest.skip("TODO: Реализовать тест для проверки значений по умолчанию в модели пользователя.")
    # TODO: Реализовать тест для проверки значений по умолчанию в модели пользователя.

    user_data = TestUserCreateSchema(
        password="StrongPassword123"
    )
    user = TestUserModel.from_orm(user_data)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.password_version == 1
    assert user.is_verified is False
    assert user.is_active is False
    assert user.role == DefaultRoles.USER.value
    assert user.last_password_change is None
    assert (datetime.now(timezone.utc) - user.signed_up_at).total_seconds() < 5  # Проверка, что дата свежая


def test_user_model_auth_provider_literal():
    """Тестирует, что auth_provider принимает только разрешенные значения."""
    TestUserModel(super_id=1, email="e1@example.com", auth_provider="email", hashed_password="pw")
    TestUserModel(super_id=2, email="e2@example.com", auth_provider="google", hashed_password="pw")
    TestUserModel(super_id=3, email="e3@example.com", auth_provider="telegram", hashed_password="pw")

    with pytest.raises(ValidationError):
        TestUserModel(super_id=4, email="e4@example.com", auth_provider="facebook", hashed_password="pw")  # type: ignore
