"""Schemas for resource-related Trapper endpoints."""
from pydantic import Field

from .base import TrapperSchema


class Resource(TrapperSchema):
    """Schema for ``/storage/api/resources`` items."""

    pk: int
    name: str
    owner: str | None = None
    owner_profile: str | None = None
    resource_type: str | None = None
    date_recorded: str | None = None

    observation_type: list[str] = Field(default_factory=list)
    species: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    url: str | None = None
    url_original: str | None = None
    mime: str | None = None
    preview_url: str | None = None
    thumbnail_url: str | None = None

    update_data: str | None = None
    detail_data: str | None = None
    delete_data: str | None = None

    date_recorded_correct: bool | None = None
