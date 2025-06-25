from pydantic import field_validator, EmailStr, Field


class EmailNormalizerMixin:
    @field_validator("email", mode="before", check_fields=False)
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()


class EmailValidatorMixin:
    @field_validator("email", mode="before", check_fields=True)
    def validate_mail(cls, v: str) -> str:
        if len(v) > 255:
            raise ValueError("Email must contain less than 255 symbols")

        return v


class PasswordValidatorMixin:
    @field_validator("password", mode="before", check_fields=False)
    def validate_password(cls, v: str) -> str:
        if not any(c.isdigit() for c in v) or not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one digit and one uppercase letter")

        if len(v) < 8:
            raise ValueError("Password must contain ate least 8 symbols")

        if len(v) > 55:
            raise ValueError("Email must contain less than 55 symbols")

        return v
