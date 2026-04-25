"""Base schemas shared across all Trapper components."""
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

TTrapperSchema = TypeVar("TTrapperSchema", bound="TrapperSchema")


class Pagination(BaseModel):
    """Pagination metadata returned by Trapper endpoints."""

    page: int = 1
    page_size: int = 0
    pages: int = 1
    count: int = 0


class TrapperSchema(BaseModel):
    """Base schema for Trapper API objects."""

    model_config = ConfigDict(extra="allow")


class PaginatedResult(BaseModel, Generic[TTrapperSchema]):
    """Normalized paginated result with typed ``results`` entries."""

    pagination: Pagination
    results: list[TTrapperSchema]
