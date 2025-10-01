from datetime import datetime, timezone
from typing import Optional, Literal, ClassVar

from sqlmodel import SQLModel, Field, Column, TIMESTAMP, String
from sqlalchemy.ext.hybrid import hybrid_property
from pydantic import EmailStr, field_validator


class UserModelBase(SQLModel, table=False):
    """ Базовая модель пользователя для SQLModel."""
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

    __id_field_name__ = "id"

    class Config:
        validate_assignment = True

    @hybrid_property
    def user_identifier(self):
        return getattr(self, self.__id_field_name__)

    @user_identifier.expression
    @classmethod
    def _user_identifier(cls):
        return getattr(cls, cls.__id_field_name__)

    user_identifier: ClassVar

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()

    def __new__(cls, *args, **kwargs):
        if cls is UserModelBase:
            raise TypeError("UserModelBase is an abstract class and cannot be instantiated. You must a redefine it.")

        return super().__new__(cls)

    def __init__(self, **kwargs):

        if "user_identifier" in kwargs:
            kwargs[self.__id_field_name__] = kwargs.pop("user_identifier")

        is_table = getattr(self.model_config, 'table', False)
        self.model_config["table"] = False
        super().__init__(**kwargs)
        self.model_config["table"] = is_table
