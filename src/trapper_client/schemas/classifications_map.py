"""Schemas for Classification map Trapper endpoint."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ResourceClassificationMap(BaseModel):
    """Resource entry embedded inside a classification map record."""

    pk: int
    name: str
    resource_type: str
    thumbnail_url: str
    date_recorded: str
    deployment: str


class ClassificationMapRecord(BaseModel):
    """Schema for ``/media_classification/api/classifications_map/`` items."""

    pk: int
    resource: ResourceClassificationMap
    static_attrs: Dict[str, Any] = Field(default_factory=dict)
    dynamic_attrs: List[Dict[str, Any]] = Field(default_factory=list)
    classify_data: str
    project: int
