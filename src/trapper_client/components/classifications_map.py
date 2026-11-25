"""
Component for the light, unpaginated list of the final classifications (the map of the classification UI).
"""

from __future__ import annotations

from trapper_client.components._classification_filters import ClassificationFiltersMixin, RequireProjectMixin
from trapper_client.components.base import TrapperComponent, versioned
from trapper_client.schemas import ClassificationMap


class ClassificationsMapComponent(RequireProjectMixin, ClassificationFiltersMixin, TrapperComponent[ClassificationMap]):
    """
    The final classifications in a light form (``client.classifications_map``), as the map of the classification
    UI uses them.

    - ``GET /media_classification/api/classifications_map`` (and ``/{pk}``): the same rows and filters as the list of
      ``client.classification_results`` (every final classification the user can see), but **not paginated** — one
      answer with every row, ``page`` and ``page_size`` do nothing — and with less in each row: the resource (its
      ``deployment`` is the ``deploymentID``), the project, and ``dynamic_attrs`` with **only the custom attributes**
      of the classificator (no observation type, species or count: use ``client.classification_results`` for them).

    **Filters:** those of the classification list (Trapper ignores any other without an error; the SDK emits an
    ``UnknownFilterWarning``):

    | Parameter | Type | Description |
    |---|---|---|
    | project | PK | The project. **Needed for deployment and collection** (``ValueError`` without it) |
    | owner | boolean | true = resources where the user is owner/manager |
    | deployment | list of PKs | Deployment PKs of the project |
    | collection | list of PKs | PK of the **link** between the project and the collection |
    | locations_map | comma-separated PKs | Location PKs |
    | rdate_from / rdate_to | date | ``date_recorded`` range |
    | rtime_from / rtime_to | HH:MM | Time-of-day range |
    | ftype | choice | Resource type (I, V, ...) |
    | classified / classified_ai | boolean | Has a classification by a user / by AI |
    | approved | boolean | Approved. Works on both versions: v1 calls it ``status`` and the SDK sends it as such |
    | bboxes | boolean | Has bounding boxes |
    | species | list of PKs | Species PKs |
    | observation_type, sex, age | choice | Observation type, sex, age |
    """

    endpoint = versioned("/media_classification/api/classifications_map", ninja="api/v2/classifications/map/")
    schema = ClassificationMap
    known_filters = ClassificationFiltersMixin._filters_for(frozenset())
