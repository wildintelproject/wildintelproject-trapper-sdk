"""
Component for User classifications data endpoint.
"""

from __future__ import annotations

from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import UserClassificationRecord


class UserClassificationsComponent(TrapperComponent[UserClassificationRecord]):
    """
    Component for ``/media_classification/api/user-classifications/``.

    Retrieve and filter user classifications from Trapper.

    Main endpoints:
    - ``GET /media_classification/api/user-classifications``: List of user classifications (paginated)
    - ``GET /media_classification/api/user-classifications/{pk}``: Single user classification detail

    **Available filter fields:**

    | Parameter        | Type                     | Description                                                                 |
    |----------------|--------------------------|-----------------------------------------------------------------------------|
    | project        | PK                       | Auto-filtrado por URL (no necesario)                                       |
    | owner          | boolean                  | true = resources where user is owner/manager                               |
    | deployment     | list of PKs              | Filter by deployment PKs                                                   |
    | collection     | list of PKs              | Filter by collection PKs                                                   |
    | locations_map  | comma-separated PKs      | Filter by location PKs                                                     |
    | rdate_from / rdate_to | date             | date_recorded range                                                        |
    | rtime_from / rtime_to | HH:MM            | Time-of-day range                                                          |
    | ftype          | choice                   | Resource type (IMAGE, VIDEO, etc.)                                         |
    | classified     | boolean                  | classified by humans                                                       |
    | classified_ai  | boolean                  | classified by AI                                                           |
    | bboxes         | boolean                  | Tiene bboxes                                                               |
    | approved       | boolean                  | Whether classification is FINAL approved                                   |
    | feedback       | boolean                  | Whether it is a feedback classification                                    |
    | species        | list of PKs              | Filter by species PKs                                                      |
    | observation_type | choice                 | Filter by observation type                                                 |
    | sex            | choice                   | Filter by sex                                                              |
    | age            | choice                   | Filter by age                                                              |

    Returns a paginated list of user classifications with support for filtering
    through query parameters.
    """

    endpoint = "/media_classification/api/user-classifications"
    schema = UserClassificationRecord