import uuid
from datetime import datetime, timezone
from typing import Optional, Literal

from sqlmodel import SQLModel, Field, Column, TIMESTAMP, String
from pydantic import EmailStr, field_validator


class UserModelBase(SQLModel, table=False):
    """ Базовая модель пользователя для SQLModel."""
    internal_id: str = Field(nullable=False, unique=True, max_length=64, default_factory=lambda : str(uuid.uuid4()))
    external_id: Optional[str] = Field(default=None, nullable=True, max_length=64)

    email: EmailStr = Field(unique=True, index=True, max_length=255)
    hashed_password: Optional[str] = Field(nullable=True, max_length=255)
    password_version: Optional[int] = Field(default=1, nullable=True)

    auth_provider: Literal["email", "google", "telegram"] = Field(sa_column=Column(String(16), nullable=False))
    user_name: Optional[str] = Field(default=None, nullable=True, max_length=255)

    is_verified: bool = Field(default=False, description="User verification status")
    is_active: bool = Field(default=False, description="User account active status")
    is_admin: bool = Field(default=False, description="User is an admin")

    signed_up_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            TIMESTAMP(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            nullable=False
        )
    )

    last_password_change: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            default=None,
            nullable=True
        )
    )

    class Config:
        validate_assignment = True

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()

    def __new__(cls, *args, **kwargs):
        if cls is UserModelBase:
            raise TypeError("UserModelBase is an abstract class and cannot be instantiated. You must a redefine it.")

        return super().__new__(cls)

    def __init__(self, **kwargs):
        is_table = getattr(self.model_config, 'table', False)
        self.model_config["table"] = False
        super().__init__(**kwargs)
        self.model_config["table"] = is_table
