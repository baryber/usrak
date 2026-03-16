from typing import Optional

from pydantic import BaseModel
from sqlmodel import Field

from usrak import TokensModelBase


class TestTokensModel(TokensModelBase, table=True):
    """Тестовая модель API токена."""

    __test__ = False
    __tablename__ = "test_tokens"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="test_users.super_id", index=True)


class TestTokensReadSchema(BaseModel):
    """Тестовая схема чтения API токена."""

    __test__ = False
    id: int | None = None
    token: str
    token_type: str
    name: str | None = None
    whitelisted_ip_addresses: list[str] | None = None
    is_deleted: bool
    expires_at: int | None = None

    model_config = {"from_attributes": True}
