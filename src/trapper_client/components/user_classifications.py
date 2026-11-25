"""
Component for the user classifications of Trapper.
"""

from __future__ import annotations

from trapper_client.components._classification_filters import RequireProjectMixin
from trapper_client.components.base import TrapperComponent, versioned
from trapper_client.schemas import UserClassification

#: Filters both versions apply to the user and AI lists.
_LIST_COMMON = frozenset({"project", "deployment", "collection", "ftype", "species", "observation_type", "bboxes",
                          "approved", "pk", "search"})

#: The filters each Trapper version applies to the user classification list (``UserClassificationFilter``).
USER_CLASSIFICATION_FILTERS = {
    "v1": _LIST_COMMON | {
        "owner", "user", "feedback", "locations_map", "rdate_from", "rdate_to", "rtime_from", "rtime_to",
        "classification", "has_bboxes", "is_feedback", "is_setup",
    },
    "v2": _LIST_COMMON | {
        "owner", "user", "feedback", "locations_map", "rdate_from", "rdate_to", "rtime_from", "rtime_to",
        "has_bboxes", "is_setup", "sex", "age", "classified", "classified_ai", "observation_level",
        "avg_confidence_min", "avg_confidence_max", "classification_type", "date_recorded", "final_classification",
        "has_animals", "has_humans", "has_unknown", "has_vehicles", "is_approved", "is_blank", "is_gold_standard",
        "model", "resource", "sequence", "tracked_species_notifications_sent_at",
    },
}


class UserClassificationsComponent(RequireProjectMixin, TrapperComponent[UserClassification]):
    """
    The classifications people made (``client.user_classifications``), before one is approved as the final one.

    - ``GET /media_classification/api/user-classifications`` (and ``/{pk}``): every user classification the user
      can see, one row per classification (a resource can have several, one per person). Read-only.

    A row has the resource, the observations (``dynamic_attrs``: type, species and count, as text) and whether it
    became the final one (``approved``). Trapper v2 does not send ``classification`` or ``created_at`` and adds
    ``is_feedback``, ``is_setup``, ``bboxes`` and ``classification_project``.

    **Filters** (Trapper ignores any other without an error; the SDK emits an ``UnknownFilterWarning``):

    | Parameter | Type | Version | Description |
    |---|---|---|---|
    | project | PK | both | Classification project. **Needed for deployment and collection** (``ValueError`` without it) |
    | deployment | list of PKs | both | Deployment PKs of the project |
    | collection | list of PKs | both | PK of the **link** between the project and the collection |
    | user | list of PKs | both | Who classified (user PKs) |
    | owner | boolean | both | true = classifications of the user |
    | approved | boolean | both | It became the final classification |
    | feedback | boolean | both | It is a feedback classification |
    | bboxes | boolean | both | Has bounding boxes |
    | ftype | choice | both | Resource type (I, V, ...) |
    | species | list of PKs | both | Species PKs |
    | observation_type | choice | both | Observation type |
    | locations_map | comma-separated PKs | both | Location PKs |
    | rdate_from / rdate_to | date | both | ``date_recorded`` range |
    | rtime_from / rtime_to | HH:MM | both | Time-of-day range |
    | search | text | both | Species (Latin or English name), resource name or attribute |
    | sex, age | choice | v2 | Sex, age |
    | classified / classified_ai | boolean | v2 | The resource has a user / AI classification |

    v2 also applies the fields of its model (``is_blank``, ``has_animals``, ``classification_type``, ...) and one
    filter per custom attribute of the project's classificator.
    """

    endpoint = versioned("/media_classification/api/user-classifications", ninja="api/v2/user-classifications/")
    schema = UserClassification
    known_filters = USER_CLASSIFICATION_FILTERS
    unknown_filter_hint = "; or the name of an attribute of the project's classificator (v2)"
