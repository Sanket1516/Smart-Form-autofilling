"""Reusable API response envelopes."""

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class ErrorPayload(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class SuccessResponse(BaseModel, Generic[DataT]):
    success: Literal[True] = True
    data: DataT | None = None
    message: str = "Operation completed successfully"


class ErrorResponse(BaseModel):
    success: Literal[False] = False
    error: ErrorPayload


class MessageResponse(BaseModel):
    success: Literal[True] = True
    message: str
