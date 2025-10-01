from datetime import datetime, timezone
from typing import Optional, ClassVar

from sqlmodel import SQLModel, Field, Column, TIMESTAMP
from sqlalchemy.ext.hybrid import hybrid_property


class TokensModelBase(SQLModel, table=False):
    """Базовая модель API токена для SQLModel."""

    token: str = Field(nullable=False, max_length=512, index=True, unique=True)
    token_type: str = Field(nullable=False, max_length=64)
    name: Optional[str] = Field(default=None, max_length=255, nullable=True)

    is_deleted: bool = Field(default=False, description="Token deletion flag")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            TIMESTAMP(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            nullable=False,
        ),
    )

    expires_at: Optional[int] = Field(default=None, nullable=True)

    __id_field_name__ = "id"
    __owner_field_name__ = "owner_identifier"

    class Config:
        validate_assignment = True

    def __new__(cls, *args, **kwargs):
        if cls is TokensModelBase:
            raise TypeError(
                "TokensModelBase is an abstract class and cannot be instantiated. "
                "You must redefine it."
            )
        return super().__new__(cls)

    @hybrid_property
    def token_identifier(self):
        return getattr(self, self.__id_field_name__)

    @token_identifier.expression
    @classmethod
    def _token_identifier(cls):
        return getattr(cls, cls.__id_field_name__)

    token_identifier: ClassVar

    @hybrid_property
    def owner_identifier(self):
        return getattr(self, self.__owner_field_name__)

    @owner_identifier.expression
    @classmethod
    def _owner_identifier(cls):
        return getattr(cls, cls.__owner_field_name__)

    owner_identifier: ClassVar