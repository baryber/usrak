from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field


DataT = TypeVar("DataT")


class CommonResponse(BaseModel):
    success: bool = Field(default=True, description="Success status")
    message: Optional[str] = Field(default=None, description="Message")


class CommonNextStepResponse(CommonResponse):
    next_step: Optional[str] = Field(
        default=None,
        description="Next step for the user. Used in async operations.",
    )


class CommonDataResponse(CommonNextStepResponse, Generic[DataT]):
    data: Optional[DataT] = Field(
        default=None,
        description="Structured payload returned by the endpoint.",
    )


class CommonDataNextStepResponse(CommonDataResponse[DataT], Generic[DataT]):
    pass
