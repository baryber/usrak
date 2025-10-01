from typing import Optional, Any

from pydantic import BaseModel


class SecretContext(BaseModel):
    password_version: Optional[int] = None
    purpose: Optional[str] = None
    ip_addresses: Optional[list[str]] = None


class JwtTokenPayloadData(BaseModel):
    token_type: str
    user_identifier: Any
    exp: Optional[int | float] = None
    jti: str
    secret_context: Optional[SecretContext] = None
