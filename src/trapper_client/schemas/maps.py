"""Schema for the umap-based Maps Trapper endpoint."""
from typing import Any, Optional

from pydantic import BaseModel


class MapRecord(BaseModel):
    """Schema for ``/geomap/api/maps`` items.

    ``center``, ``locate``, and ``tilelayer`` come from the third-party
    ``django-umap`` ``Map`` model (not part of this repo), so their exact
    JSON shape hasn't been verified against a live server; they are kept
    as ``Any`` rather than guessing a stricter type.
    """

    pk: int
    slug: Optional[str] = None
    description: Optional[str] = None
    center: Any = None
    zoom: Optional[float] = None
    locate: Any = None
    licence: Optional[str] = None
    modified_at: Optional[str] = None
    tilelayer: Any = None
    owner: Optional[str] = None
    owner_profile: Optional[str] = None
    edit_status: Optional[str] = None
    share_status: Optional[str] = None
    settings: Any = None
    delete_data: Optional[str] = None
    detail_data: Optional[str] = None
