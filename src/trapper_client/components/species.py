"""
Component for the Species taxonomy data endpoint.
"""

from __future__ import annotations

from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import SpeciesRecord


class SpeciesComponent(TrapperComponent[SpeciesRecord]):
    """
    Component for ``/tables/api/species``.

    Retrieve and filter the species taxonomy table from Trapper. Species
    PKs returned here are the same ones referenced by the ``species``
    filter on classification-related components (e.g. ``classifications``,
    ``ai_classifications``).

    Main endpoints:
    - ``GET /tables/api/species``: List of species (paginated)
    - ``GET /tables/api/species/{pk}``: Single species detail

    **Available filter fields:**

    | Parameter    | Type   | Description                                       |
    |--------------|--------|-----------------------------------------------------|
    | english_name | string | Filter by exact english name                        |
    | latin_name   | string | Filter by exact latin name                          |
    | search       | string | Free-text search across english_name, latin_name    |
    """

    endpoint = "tables/api/species"
    schema = SpeciesRecord
