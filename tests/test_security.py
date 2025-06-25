import pytest

from datetime import datetime, timedelta, timezone

from usrak.core import security, exceptions as exc
from usrak.core.schemas.security import JwtTokenPayloadData, SecretContext
from usrak import AppConfig


@pytest.fixture(autouse=True)
def setup_app_config(app_config: AppConfig):
    """Устанавливает глобальную конфигурацию для функций безопасности."""
    from usrak.core.dependencies.config_provider import set_app_config
    set_app_config(app_config)


def test_generate_jti():
    jti1 = security.generate_jti()
    jti2 = security.generate_jti()
    assert isinstance(jti1, str)
    assert len(jti1) == 36  # UUID format
    assert jti1 != jti2


def test_password_hashing_and_verification():
    password = "StrongPassword123"
    hashed_password = security.hash_password(password)
    assert isinstance(hashed_password, str)
    assert hashed_password != password
    assert security.verify_password(password, hashed_password)
    assert not security.verify_password("WrongPassword", hashed_password)


def test_token_encryption_decryption():
    original_token = "this_is_a_secret_token_string"
    encrypted_token = security.encrypt_token(original_token)
    assert isinstance(encrypted_token, str)
    assert encrypted_token != original_token

    decrypted_token = security.decrypt_token(encrypted_token)
    assert decrypted_token == original_token


def test_decrypt_invalid_token():
    assert security.decrypt_token("invalid_encrypted_string") is None


def test_jwt_creation_and_decoding(app_config: AppConfig):
    user_id = "test_user"
    secret_key = app_config.JWT_ACCESS_TOKEN_SECRET_KEY

    payload_data = JwtTokenPayloadData(
        token_type="access",
        user_identifier=user_id,
        exp=datetime.now(timezone.utc) + timedelta(minutes=15),
        jti=security.generate_jti(),
        secret_context=SecretContext(password_version=1, purpose="login")
    )

    token = security.create_jwt_token(payload_data, secret_key)
    assert isinstance(token, str)

    decoded_payload = security.decode_jwt_token(token, secret_key)
    assert decoded_payload.user_identifier == user_id
    assert decoded_payload.token_type == "access"
    assert decoded_payload.secret_context
    if decoded_payload.secret_context:  # Проверка для mypy
        assert decoded_payload.secret_context.password_version == 1
        assert decoded_payload.secret_context.purpose == "login"


def test_jwt_expired_token(app_config: AppConfig):
    user_id = "test_user_expired"
    secret_key = app_config.JWT_ACCESS_TOKEN_SECRET_KEY

    payload_data = JwtTokenPayloadData(
        token_type="access",
        user_identifier=user_id,
        exp=datetime.now(timezone.utc) - timedelta(minutes=1),  # Токен уже истек
        jti=security.generate_jti()
    )

    token = security.create_jwt_token(payload_data, secret_key)

    with pytest.raises(exc.ExpiredAccessTokenException):
        security.decode_jwt_token(token, secret_key)


def test_jwt_invalid_signature(app_config: AppConfig):
    user_id = "test_user_invalid_sig"
    secret_key = app_config.JWT_ACCESS_TOKEN_SECRET_KEY
    wrong_secret_key = "thisisawrongsecretkey1234567890"

    payload_data = JwtTokenPayloadData(
        token_type="access",
        user_identifier=user_id,
        exp=datetime.now(timezone.utc) + timedelta(minutes=15),
        jti=security.generate_jti()
    )

    token = security.create_jwt_token(payload_data, secret_key)

    with pytest.raises(exc.InvalidAccessTokenException):  # PyJWTError (родительский для InvalidSignatureError)
        security.decode_jwt_token(token, wrong_secret_key)


def test_jwt_malformed_token(app_config: AppConfig):
    malformed_token = "this.is.not.a.valid.jwt"
    secret_key = app_config.JWT_ACCESS_TOKEN_SECRET_KEY
    with pytest.raises(exc.InvalidAccessTokenException):  # PyJWTError (родительский для DecodeError)
        security.decode_jwt_token(malformed_token, secret_key)


def test_verify_secret_context():
    context1 = SecretContext(password_version=1, purpose="login", ip_address="127.0.0.1")

    # Точное совпадение
    expected1 = SecretContext(password_version=1, purpose="login", ip_address="127.0.0.1")
    assert security.verify_secret_context(context1, expected1)

    # Несовпадение значения
    expected2 = SecretContext(password_version=2, purpose="login")
    assert not security.verify_secret_context(context1, expected2)

    # Несовпадение поля
    expected3 = SecretContext(password_version=1, purpose="reset")
    assert not security.verify_secret_context(context1, expected3)

    # Context имеет меньше полей, чем expected (должно быть False, если expected требует больше)
    # По логике verify_secret_context: он проверяет, что все поля из context_dict есть в expected_dict и совпадают.
    # Если expected_dict имеет поля, которых нет в context_dict, это не проверяется.
    # Это означает, что context может быть "подмножеством" expected.
    # Если же context имеет поля, которых нет в expected, это приведет к False.

    context_minimal = SecretContext(password_version=1)
    expected_full = SecretContext(password_version=1, purpose="test")
    # context_minimal не имеет 'purpose', которое есть в expected_full.
    # Логика функции:
    # for key, value in context_dict.items(): -> key='password_version'
    #   if key not in expected_dict or expected_dict[key] != value:
    # Эта проверка пройдет.
    # Таким образом, функция проверяет, что context является "совместимым подмножеством" expected.
    assert security.verify_secret_context(context_minimal, expected_full)  # True, т.к. password_version совпадает

    # Случай, когда context имеет поле, которого нет в expected
    context_extra = SecretContext(password_version=1, extra_field="value")  # type: ignore
    expected_simple = SecretContext(password_version=1)
    # В этом случае context_dict будет {'password_version': 1, 'extra_field': 'value'}
    # expected_dict будет {'password_version': 1}
    # При проверке 'extra_field', `key not in expected_dict` будет True, вернет False.
    assert not security.verify_secret_context(context_extra, expected_simple)

    # Пустые контексты
    empty_context = SecretContext()
    empty_expected = SecretContext()
    assert security.verify_secret_context(empty_context, empty_expected)

    non_empty_context = SecretContext(password_version=1)
    assert security.verify_secret_context(non_empty_context,
                                          empty_expected)  # True, т.к. в empty_expected нет полей для проверки

    assert not security.verify_secret_context(empty_context,
                                              non_empty_context)  # False, т.к. password_version нет в empty_context