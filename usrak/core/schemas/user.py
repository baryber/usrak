from typing import Optional, Literal

from pydantic import BaseModel, Field
from pydantic import EmailStr, model_validator

from usrak.core.schemas.mixins import EmailNormalizerMixin, PasswordValidatorMixin


class UserLogin(
    BaseModel,
):
    auth_provider: Literal["email"]
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=255)


class UserCreate(
    BaseModel,
    EmailNormalizerMixin,
    PasswordValidatorMixin,
):
    auth_provider: Literal["email", "google", "telegram"]

    email: Optional[EmailStr] = Field(default=None, max_length=255)
    password: Optional[str] = Field(default=None, min_length=8, max_length=255)

    external_id: Optional[str] = Field(default=None, max_length=64)
    user_name: Optional[str] = Field(default=None, max_length=255)
    # TODO: remove external id and user name from email auth

    @model_validator(mode="after")
    def validate_auth_provider(self):
        if self.auth_provider == "email":
            if not self.email or not self.password:
                raise ValueError("Email and password are required for email auth and must not be empty")

        elif self.auth_provider == "google":
            if not self.email:
                raise ValueError("Email is required for Google auth and must not be empty")

        elif self.auth_provider == "telegram":
            if not self.external_id or not self.user_name:
                raise ValueError("External ID and user name are required for Telegram auth and must not be empty")

        return self


if __name__ == '__main__':
    test = UserLogin(
        auth_provider="email",
        email="test@GMail.coM ",
        password="Test123"
    )
    print(test)
