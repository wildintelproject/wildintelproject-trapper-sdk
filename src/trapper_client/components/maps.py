"""
Component for the umap-based Maps data endpoint.
"""

from __future__ import annotations

from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import MapRecord


class MapsComponent(TrapperComponent[MapRecord]):
    """
    Component for ``/geomap/api/maps``.

    Retrieve and filter the umap-based maps accessible to the current user.

    Main endpoints:
    - ``GET /geomap/api/maps``: List of maps (paginated)
    - ``GET /geomap/api/maps/{pk}``: Single map detail

    **Available filter fields:**

    | Parameter | Type    | Description                                              |
    |-----------|---------|-----------------------------------------------------------|
    | owner     | boolean | true = maps owned by the current user                     |
    | search    | string  | Free-text search across name, description, owner__username |
    """

    endpoint = "geomap/api/maps"
    schema = MapRecord
