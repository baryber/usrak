from typing import Optional, TypeVar, Generic

from pydantic import BaseModel, Field


T = TypeVar("T")


class CommonResponse(BaseModel):
    success: bool = Field(default=True, description="Success status")
    message: Optional[str] = Field(default=None, description="Message")


class CommonDataResponse(Generic[T], CommonResponse):
    data: Optional[T] = Field(default=None, description="Data")


class CommonNextStepResponse(CommonResponse):
    next_step: Optional[str] = Field(
        default=None,
        description="Next step for the user. Used in async operations.",
    )


class CommonDataNextStepResponse(CommonDataResponse, CommonNextStepResponse):
    pass
