from typing import Optional

from pydantic import BaseModel, Field


class ApiTokenCreate(BaseModel):
    name: str = Field(max_length=255)
    description: Optional[str] = Field(default=None, max_length=1024)
    expires_at: Optional[int] = Field(default=None, description="Expiration timestamp datetime in seconds")
    whitelisted_ip_addresses: Optional[list[str]] = Field(
        default=None,
        description="List of whitelisted IP addresses. If set, the token will be valid only for requests from these IP addresses."
    )
