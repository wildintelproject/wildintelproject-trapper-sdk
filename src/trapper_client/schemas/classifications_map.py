"""Schemas for Classification map Trapper endpoint."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from trapper_client._deprecated import deprecated_getattr


class ResourceClassificationMap(BaseModel):
    """Resource entry embedded inside a classification map record."""

    pk: int
    name: str
    resource_type: str
    thumbnail_url: str
    date_recorded: str
    deployment: str


class ClassificationMap(BaseModel):
    """Schema for ``/media_classification/api/classifications_map/`` items."""

    pk: int
    resource: ResourceClassificationMap
    static_attrs: Dict[str, Any] = Field(default_factory=dict)
    dynamic_attrs: List[Dict[str, Any]] = Field(default_factory=list)
    classify_data: Optional[str] = None  # null in Trapper v2
    project: int


__getattr__ = deprecated_getattr(__name__)
