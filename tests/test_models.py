import pytest
from pydantic import ValidationError
from datetime import datetime, timezone

from usrak.core.models.user import UserModelBase
from tests.fixtures.user import TestUserCreateSchema, TestUserModel


def test_user_model_base_cannot_be_instantiated():
    """Тестирует, что UserModelBase не может быть инстанциирован напрямую."""
    with pytest.raises(TypeError, match="UserModelBase is an abstract class and cannot be instantiated."):
        UserModelBase(super_id="test", email="test@example.com", auth_provider="email")


def test_test_user_model_creation(db_session):  # db_session для потенциального сохранения
    """Тестирует создание экземпляра TestUserModel (наследника UserModelBase)."""
    user_data = {
        "super_id": 123,
        "email": "test@example.com",
        "auth_provider": "email",
        "hashed_password": "hashed_pw",
        "extra_field": "extra_data"
    }
    user = TestUserModel(**user_data)

    assert user.user_identifier == "user123"
    assert user.email == "test@example.com"  # Нормализация должна произойти при валидации Pydantic
    assert user.auth_provider == "email"
    assert user.hashed_password == "hashed_pw"
    assert user.extra_field == "extra_data"
    assert user.is_verified is False  # Default
    assert user.is_active is False  # Default
    assert user.is_admin is False  # Default
    assert isinstance(user.signed_up_at, datetime)
    assert user.signed_up_at.tzinfo == timezone.utc


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
    assert user.is_admin is False
    assert user.last_password_change is None
    assert (datetime.now(timezone.utc) - user.signed_up_at).total_seconds() < 5  # Проверка, что дата свежая


def test_user_model_auth_provider_literal():
    """Тестирует, что auth_provider принимает только разрешенные значения."""
    TestUserModel(super_id=1, email="e1@example.com", auth_provider="email")
    TestUserModel(super_id=2, email="e2@example.com", auth_provider="google")
    TestUserModel(super_id=3, email="e3@example.com", auth_provider="telegram")

    with pytest.raises(ValidationError):
        TestUserModel(super_id=4, email="e4@example.com", auth_provider="facebook")  # type: ignore
