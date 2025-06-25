from datetime import datetime, timezone
from pydantic import BaseModel


class RateLimitObj(BaseModel):
    value: str
    created_at: datetime
