"""Schemas for User classification Trapper endpoints."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator
from trapper_client._deprecated import deprecated_getattr


class ResourceUser(BaseModel):
    """Resource entry embedded inside a User classification record."""

    pk: int
    name: str
    resource_type: str
    thumbnail_url: str
    url: str
    mime: str
    date_recorded: str
    deployment: int
    deployment_id: str


class UserObservationAttr(BaseModel):
    """A single observation attribute returned by the User classifier."""

    observation_type: str
    species: Optional[str] = None
    count: Optional[str] = None
    classification_confidence: Optional[str] = None

    @field_validator("observation_type", "species", "count", "classification_confidence", mode="before")
    @classmethod
    def _unwrap_value(cls, v: Any) -> Any:
        """Trapper v2 wraps each attribute as ``{"value": ...}``; v1 sends the bare value."""
        if isinstance(v, dict) and "value" in v:
            return v["value"]
        return v


class UserClassification(BaseModel):
    """Schema for ``/media_classification/api/user-classifications`` items."""

    pk: int
    owner: str
    owner_profile: Optional[str] = None  # null in Trapper v2
    classification: Optional[int] = None  # absent in Trapper v2
    resource: ResourceUser

    collection: Optional[int] = None
    updated_at: Optional[str] = None
    created_at: Optional[str] = None
    approved: Optional[bool] = None

    static_attrs: Dict[str, Any] = Field(default_factory=dict)
    dynamic_attrs: List[UserObservationAttr] = Field(default_factory=list)

    detail_data: Optional[str] = None
    delete_data: Optional[str] = None
    ai_provider: Optional[str] = None


__getattr__ = deprecated_getattr(__name__)
