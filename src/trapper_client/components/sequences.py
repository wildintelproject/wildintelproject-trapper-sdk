"""
Component for the Sequences data endpoint.
"""

from __future__ import annotations

from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import SequenceRecord


class SequencesComponent(TrapperComponent[SequenceRecord]):
    """
    Component for ``/media_classification/api/sequences``.

    Retrieve and filter resource sequences (events grouping resources
    recorded within a configurable time interval of each other).

    Main endpoints:
    - ``GET /media_classification/api/sequences``: List of sequences
      (this endpoint is **not paginated** server-side; ``get_all``/``where``
      still work transparently since a single unpaginated page is treated
      as page 1 of 1)
    - ``GET /media_classification/api/sequences/{pk}``: Single sequence detail

    **Available filter fields:**

    | Parameter     | Type                | Description                                  |
    |---------------|---------------------|-----------------------------------------------|
    | sequence_id   | int                 | Filter by sequence id                          |
    | sequence_uuid | str                 | Filter by sequence UUID                        |
    | interval      | int                 | Filter by grouping interval (seconds)          |
    | collection    | PK                  | Filter by classification-project-collection PK |
    | deployment    | comma-separated PKs | Filter by deployment PKs of member resources   |
    """

    endpoint = "media_classification/api/sequences"
    schema = SequenceRecord
