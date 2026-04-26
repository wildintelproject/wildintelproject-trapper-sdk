"""
Component for Classification map data endpoint.
"""

from __future__ import annotations

from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import ClassificationMapRecord


class ClassificationsMapComponent(TrapperComponent[ClassificationMapRecord]):
    """
    Component for ``/media_classification/api/classifications_map/``.

    Retrieve and filter resources pending classification for a given project.

    Main endpoints:
    - ``GET /media_classification/api/classifications_map``: List of resources to classify (paginated)
    - ``GET /media_classification/api/classifications_map/{pk}``: Single record detail

    **Available filter fields:**

    | Parameter        | Type                     | Description                                                                 |
    |----------------|--------------------------|-----------------------------------------------------------------------------|
    | project        | PK                       | Filter by classification project PK                                        |
    | owner          | boolean                  | true = resources where user is owner/manager                               |
    | deployment     | list of PKs              | Filter by deployment PKs                                                   |
    | collection     | list of PKs              | Filter by collection PKs                                                   |
    | locations_map  | comma-separated PKs      | Filter by location PKs                                                     |
    | rdate_from / rdate_to | date             | date_recorded range                                                        |
    | rtime_from / rtime_to | HH:MM            | Time-of-day range                                                          |
    | ftype          | choice                   | Resource type (IMAGE, VIDEO, etc.)                                         |
    | classified     | boolean                  | Filter by whether resource has been classified by humans                   |
    | classified_ai  | boolean                  | Filter by whether resource has been classified by AI                       |
    | approved       | boolean                  | Whether classification is FINAL approved                                   |
    | species        | list of PKs              | Filter by species PKs                                                      |
    | observation_type | choice                 | Filter by observation type                                                 |

    Returns a paginated list of resources pending classification with support for
    filtering through query parameters.
    """

    endpoint = "/media_classification/api/classifications_map"
    schema = ClassificationMapRecord
