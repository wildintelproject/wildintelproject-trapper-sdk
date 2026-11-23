"""Base schemas shared across all Trapper components."""
from typing import Generic, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict

TTrapperSchema = TypeVar("TTrapperSchema", bound="TrapperSchema")


def choice(enum: type) -> BeforeValidator:
    """Validator for a field typed with one of :mod:`trapper_client.enums`: it accepts the enum's
    member, number or label, whatever ``enum.parse()`` accepts."""
    return BeforeValidator(lambda value: enum.parse(value, enum.__name__))


class Pagination(BaseModel):
    """Pagination metadata returned by Trapper endpoints."""

    page: int = 1
    page_size: int = 0
    pages: int = 1
    count: int = 0
    total: int | None = None
    filtered: int | None = None


class TrapperSchema(BaseModel):
    """Base schema for Trapper API objects."""

    model_config = ConfigDict(extra="allow")


class PaginatedResult(BaseModel, Generic[TTrapperSchema]):
    """Normalized paginated result with typed ``results`` entries."""

    pagination: Pagination
    results: list[TTrapperSchema]
