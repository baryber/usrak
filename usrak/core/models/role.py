from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class RoleModelBase(SQLModel, table=False):
    """Base role model for SQLModel."""

    name: str = Field(nullable=False, max_length=64, description="Role identifier")
    description: str | None = Field(default=None, nullable=True, max_length=255)
    user_management_rules: dict[str, list[str]] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="Per-role management rules override.",
    )

    class Config:
        validate_assignment = True

    def __new__(cls, *args, **kwargs):
        if cls is RoleModelBase:
            raise TypeError(
                "RoleModelBase is an abstract class and cannot be instantiated. You must redefine it."
            )
        return super().__new__(cls)
