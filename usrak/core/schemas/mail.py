from sqlmodel import Field
from pydantic import EmailStr, BaseModel, field_validator


class Mail(BaseModel):
    subject: str = Field(max_length=255)
    body: str = Field(max_length=65535)
    receiver: EmailStr

    @field_validator("subject")
    def validate_subject(cls, v: str) -> str:
        if "\n" in v or "\r" in v:
            raise ValueError("Subject must not contain newlines")

        return v.strip()

    @field_validator("body")
    def validate_body(cls, v: str) -> str:
        return v.strip()


class EmailRequestCodeInput(BaseModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(max_length=255, min_length=8)

    @field_validator("email")
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("password")
    def validate_password(cls, v: str) -> str:
        if not any(c.isdigit() for c in v) or not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one digit and one uppercase letter")
        return v


class EmailVerificationInput(BaseModel):
    email: EmailStr = Field(max_length=255)
    token: str = Field(max_length=255, regex=r"^\d{6}$")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()
