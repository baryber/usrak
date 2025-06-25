from typing import Optional
from typing_extensions import TypedDict
from datetime import datetime

from pydantic import BaseModel


class SecretContext(BaseModel):
    password_version: Optional[int] = None
    purpose: Optional[str] = None
    ip_address: Optional[str] = None


class JwtTokenPayloadData(BaseModel):
    token_type: str
    user_identifier: str
    exp: datetime
    jti: str
    secret_context: Optional[SecretContext] = None
