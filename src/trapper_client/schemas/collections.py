"""Schemas for collection-related Trapper endpoints."""
from typing import Optional

from .base import TrapperSchema


class Collection(TrapperSchema):
    """Schema for ``/storage/api/collections/`` items."""

    pk: int
    name: str
    owner: Optional[str] = None
    owner_profile: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    update_data: Optional[str] = None
    detail_data: Optional[str] = None
    delete_data: Optional[str] = None


class CollectionCP(TrapperSchema):
    """Schema for a collection entry inside a classification project."""

    pk: int
    collection_pk: int
    name: str
    status: str
    is_active: bool
    detail_data: str
    classify_data: str
    approved_count: int
    classified_count: int
    total_count: int
