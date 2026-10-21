from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int


class ErrorBody(BaseModel):
    status: int
    type: str
    message: str
    details: list | dict | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
