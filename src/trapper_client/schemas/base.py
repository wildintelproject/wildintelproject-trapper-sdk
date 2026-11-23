"""Base schemas shared across all Trapper components."""
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, TypeAdapter, ValidationError

TTrapperSchema = TypeVar("TTrapperSchema", bound="TrapperSchema")


def choice(enum: type) -> BeforeValidator:
    """Validator for a field typed with one of :mod:`trapper_client.enums`: it accepts the enum's
    member, number or label, whatever ``enum.parse()`` accepts."""
    return BeforeValidator(lambda value: enum.parse(value, enum.__name__))


_DATETIME = TypeAdapter(datetime)


def read_datetime(value: Any) -> Any:
    """Read a date from Trapper as a timezone-aware ``datetime``.

    Trapper writes the same instant as ``2024-01-01T00:00:00+01:00`` in a JSON list and as
    ``2024-01-01T00:00:00+0100`` in a CSV export. An empty value is ``None``; one that cannot be read is kept
    as it came, so that a strange value does not break a listing.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return _DATETIME.validate_python(value.strip() if isinstance(value, str) else value)
    except ValidationError:
        return value


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
