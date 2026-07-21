"""Schemas for research-project-related Trapper endpoints."""
from datetime import datetime

from pydantic import Field

from .base import TrapperSchema


class ResearchProjectRole(TrapperSchema):
    """Role entry inside ``ResearchProject.project_roles``."""

    user: str | None = None
    username: str | None = None
    profile: str | None = None
    roles: list[str] = Field(default_factory=list)


class ResearchProjectCollection(TrapperSchema):
    """Schema for ``/research/api/project/{project_pk}/collections`` items."""

    pk: int
    collection_pk: int | None = None
    name: str | None = None
    owner: str | None = None
    owner_profile: str | None = None
    status: bool | int | str | None = None
    date_created: datetime | str | None = None
    description: str | None = None
    detail_data: str | None = None
    delete_data: str | None = None


class ResearchProject(TrapperSchema):
    """Schema for ``/research/api/projects`` items."""

    pk: int
    name: str | None = None
    owner: str | None = None
    owner_profile: str | None = None
    acronym: str | None = None

    keywords: list[str] = Field(default_factory=list)
    date_created: datetime | str | None = None
    project_roles: list[ResearchProjectRole] = Field(default_factory=list)

    update_data: str | None = None
    detail_data: str | None = None
    delete_data: str | None = None

    status: bool | int | str | None = None
