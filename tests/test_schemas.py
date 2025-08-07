import pytest
from datetime import datetime, timezone, timedelta

from pydantic import ValidationError

from usrak.core.schemas.mail import Mail, EmailRequestCodeInput, EmailVerificationInput
from usrak.core.schemas.password import ForgotPasswordRequestInput, VerifyResetPasswordTokenInput, \
    PasswordResetVerificationInput
from usrak.core.schemas.redis import RateLimitObj
from usrak.core.schemas.response import StatusResponse
from usrak.core.schemas.security import SecretContext, JwtTokenPayloadData
from usrak.core.schemas.user import UserLogin, UserCreate


# Тесты для usrak.core.schemas.mail
def test_mail_schema_valid():
    mail = Mail(subject="Test Subject", body="Test body", receiver="test@example.com")
    assert mail.subject == "Test Subject"
    assert mail.body == "Test body"
    assert mail.receiver == "test@example.com"


def test_mail_schema_subject_newline():
    with pytest.raises(ValidationError, match="Subject must not contain newlines"):
        Mail(subject="Test\nSubject", body="Test body", receiver="test@example.com")


def test_mail_schema_stripping():
    mail = Mail(subject="  Test Subject  ", body="  Test body  ", receiver="test@example.com")
    assert mail.subject == "Test Subject"
    assert mail.body == "Test body"


def test_email_request_code_input_valid():
    data = EmailRequestCodeInput(email=" test@example.com ", password="Password1")
    assert data.email == "test@example.com"
    assert data.password == "Password1"


@pytest.mark.parametrize("invalid_password", ["nouppercase1", "NODIGITPW"])
def test_email_request_code_input_invalid_password(invalid_password: str):
    with pytest.raises(ValidationError, match="Password must contain at least one digit and one uppercase letter"):
        EmailRequestCodeInput(email="test@example.com", password=invalid_password)


def test_short_password():
    with pytest.raises(ValidationError, match="String should have at least 8 characters"):
        EmailRequestCodeInput(email="test@example.com", password="short")


def test_email_verification_input_valid():
    data = EmailVerificationInput(email=" test@example.com ", token="123456")
    assert data.email == "test@example.com"
    assert data.token == "123456"


def test_email_verification_input_invalid_token():
    with pytest.raises(ValidationError):  # Regex validation
        EmailVerificationInput(email="test@example.com", token="12345")
    with pytest.raises(ValidationError):
        EmailVerificationInput(email="test@example.com", token="abcdef")


# Тесты для usrak.core.schemas.password
def test_forgot_password_request_input_valid():
    data = ForgotPasswordRequestInput(email=" test@example.com ")
    assert data.email == "test@example.com"


def test_verify_reset_password_token_input_valid():
    data = VerifyResetPasswordTokenInput(email=" test@example.com ", token="some_token_value")
    assert data.email == "test@example.com"
    assert data.token == "some_token_value"


def test_password_reset_verification_input_valid():
    data = PasswordResetVerificationInput(
        email=" test@example.com ",
        token="valid_token",
        new_password="NewPassword1"
    )
    assert data.email == "test@example.com"
    assert data.new_password == "NewPassword1"


@pytest.mark.parametrize("invalid_password", ["nouppercase1", "NODIGIT"])
def test_password_reset_verification_input_invalid_password(invalid_password: str):
    with pytest.raises(ValidationError, match="Password must contain at least one digit and one uppercase letter"):
        PasswordResetVerificationInput(
            email="test@example.com",
            token="token",
            new_password=invalid_password
        )


# Тесты для usrak.core.schemas.redis
def test_rate_limit_obj_valid():
    now = datetime.now(timezone.utc)
    obj = RateLimitObj(value="hashed_value", created_at=now)
    assert obj.value == "hashed_value"
    assert obj.created_at == now


# Тесты для usrak.core.schemas.response
def test_status_response_defaults():
    resp = StatusResponse()
    assert resp.success is True
    assert resp.message is None
    assert resp.data is None
    assert resp.next_step is None


def test_status_response_custom():
    resp = StatusResponse(success=False, message="Error", data={"key": "value"}, next_step="verify")
    assert resp.success is False
    assert resp.message == "Error"
    assert resp.data == {"key": "value"}
    assert resp.next_step == "verify"


# Тесты для usrak.core.schemas.security
def test_secret_context_valid():
    ctx = SecretContext(password_version=1, purpose="login", ip_address="127.0.0.1")
    assert ctx.password_version == 1
    assert ctx.purpose == "login"
    assert ctx.ip_address == "127.0.0.1"


def test_jwt_token_payload_data_valid():
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=15)
    jti = "test_jti"
    secret_ctx = SecretContext(password_version=1)
    payload = JwtTokenPayloadData(
        token_type="access",
        user_identifier="user123",
        exp=exp,
        jti=jti,
        secret_context=secret_ctx
    )
    assert payload.token_type == "access"
    assert payload.user_identifier == "user123"
    assert payload.exp == exp
    assert payload.jti == jti
    assert payload.secret_context == secret_ctx


# Тесты для usrak.core.schemas.user
def test_user_login_valid():
    data = UserLogin(auth_provider="email", email="test@example.com", password="Password123")
    assert data.auth_provider == "email"
    assert data.email == "test@example.com"  # EmailStr handles normalization if any
    assert data.password == "Password123"


def test_user_create_email_valid():
    data = UserCreate(auth_provider="email", email=" Test@Example.COM ", password="Password1Valid")
    assert data.auth_provider == "email"
    assert data.email == "test@example.com"  # Normalized by EmailNormalizerMixin
    assert data.password == "Password1Valid"  # Validated by PasswordValidatorMixin


@pytest.mark.parametrize("invalid_password", ["Sh0rt", "nouppercase1", "NooDIGIT", "tOOlongpassword" * 10])
def test_user_create_email_invalid_password(invalid_password: str):
    expected_error_msg = "Password must contain at least one digit and one uppercase letter"
    if len(invalid_password) < 8:
        expected_error_msg = "Password must contain ate least 8 symbols"
    if len(invalid_password) > 55:
        expected_error_msg = "Email must contain less than 55 symbols"  # Опечатка в сообщении, должно быть "Password"

    with pytest.raises(ValidationError, match=expected_error_msg):
        UserCreate(auth_provider="email", email="test@example.com", password=invalid_password)


def test_user_create_google_valid():
    data = UserCreate(auth_provider="google", email="googleuser@example.com", external_id="google_id_123",
                      user_name="Google User")
    assert data.auth_provider == "google"
    assert data.email == "googleuser@example.com"
    assert data.external_id == "google_id_123"  # external_id и user_name не обязательны для google по схеме, но могут быть
    assert data.user_name == "Google User"


def test_user_create_telegram_valid():
    data = UserCreate(auth_provider="telegram", external_id="tele_id_456", user_name="Tele User")
    assert data.auth_provider == "telegram"
    assert data.external_id == "tele_id_456"
    assert data.user_name == "Tele User"
    assert data.email is None  # Email не обязателен для telegram по схеме


def test_user_create_model_validator_email_missing_fields():
    with pytest.raises(ValueError, match="Email and password are required for email auth and must not be empty"):
        UserCreate(auth_provider="email")
    with pytest.raises(ValueError, match="Email and password are required for email auth and must not be empty"):
        UserCreate(auth_provider="email", email="test@example.com")  # Нет пароля
    with pytest.raises(ValueError, match="Email and password are required for email auth and must not be empty"):
        UserCreate(auth_provider="email", password="Password1")  # Нет email


def test_user_create_model_validator_google_missing_fields():
    with pytest.raises(ValueError, match="Email is required for Google auth and must not be empty"):
        UserCreate(auth_provider="google")  # Нет email


def test_user_create_model_validator_telegram_missing_fields():
    with pytest.raises(ValueError,
                       match="External ID and user name are required for Telegram auth and must not be empty"):
        UserCreate(auth_provider="telegram")
    with pytest.raises(ValueError,
                       match="External ID and user name are required for Telegram auth and must not be empty"):
        UserCreate(auth_provider="telegram", external_id="tele_id")  # Нет user_name
    with pytest.raises(ValueError,
                       match="External ID and user name are required for Telegram auth and must not be empty"):
        UserCreate(auth_provider="telegram", user_name="Tele User")  # Нет external_id
