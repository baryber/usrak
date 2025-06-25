from pydantic import BaseModel, field_validator, EmailStr, Field

from usrak.core.schemas.mixins import EmailNormalizerMixin, EmailValidatorMixin


class ForgotPasswordRequestInput(
    BaseModel,
    EmailNormalizerMixin,
    EmailValidatorMixin
):
    email: EmailStr = Field()


class VerifyResetPasswordTokenInput(
    BaseModel,
    EmailValidatorMixin,
    EmailNormalizerMixin
):
    email: EmailStr = Field()
    token: str = Field(max_length=255)


# TODO: add validators below if need
class PasswordResetVerificationInput(
    BaseModel,
    EmailValidatorMixin,
    EmailNormalizerMixin,
):
    email: EmailStr = Field(max_length=255)
    token: str = Field(max_length=255)
    new_password: str = Field(max_length=255, min_length=8)

    @field_validator("new_password")
    def validate_password(cls, v: str) -> str:
        if not any(c.isdigit() for c in v) or not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one digit and one uppercase letter")

        return v


if __name__ == '__main__':
    mailt = ForgotPasswordRequestInput(
        email="sA@maIl.ru "
    )
    print(mailt)
