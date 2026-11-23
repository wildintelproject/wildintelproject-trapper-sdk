"""Schemas for Classificators Trapper endpoint."""
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ClassificatorRecord(BaseModel):
    """Schema for ``/api/classificators/`` items."""

    pk: int
    name: str
    owner: str
    owner_profile: Optional[str] = None  # null in Trapper v2
    updated_date: str

    predefined_attrs: Dict[str, Any] = Field(default_factory=dict)
    custom_attrs: Dict[str, Any] = Field(default_factory=dict)

    static_attrs_order: Optional[str] = None
    dynamic_attrs_order: Optional[str] = None
    description: Optional[str] = None

    update_data: Optional[str] = None
    detail_data: Optional[str] = None
    delete_data: Optional[str] = None
