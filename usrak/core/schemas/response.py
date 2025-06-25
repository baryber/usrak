from typing import Optional, Any

from pydantic import BaseModel, Field


class StatusResponse(BaseModel):
    success: bool = Field(default=True, description="Success status")
    message: Optional[str] = Field(default=None, description="Message")
    data: Optional[Any] = Field(default=None, description="Data")
    next_step: Optional[str] = Field(
        default=None,
        description="Next step for the user. Used in async operations.",
    )
