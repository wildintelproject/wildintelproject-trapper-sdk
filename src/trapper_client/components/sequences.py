"""
Component for the sequences of Trapper (events: resources recorded close in time).
"""

from __future__ import annotations

from typing import Any, Dict

from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import Sequence

_SEQUENCE_FILTERS = frozenset({"sequence_id", "sequence_uuid", "interval", "collection", "deployment", "pk"})


class SequencesComponent(TrapperComponent[Sequence]):
    """
    The sequences of Trapper (``client.sequences``): groups of resources recorded within ``interval`` seconds of each
    other in a collection of a classification project, the events of Camtrap DP (``eventID``).

    - ``GET /media_classification/api/sequences`` (and ``/{pk}``): **not paginated** (one answer with every row;
      ``page``/``page_size`` do nothing) and **not limited to what the user can see**: every sequence of the server.
      Read-only: Trapper builds them in the classification UI.

    A row has ``sequence_id`` (its number inside the collection), ``sequence_uuid`` (the ``eventID``),
    ``resources`` (the resource PKs; Trapper v2 repeats a resource once per classification of it, the SDK keeps one)
    and ``created_at``.

    **Filters** (Trapper ignores any other without an error; the SDK emits an ``UnknownFilterWarning``):

    | Parameter | Type | Description |
    |---|---|---|
    | sequence_id | int | Number of the sequence inside its collection |
    | sequence_uuid | str | UUID (the ``eventID``) |
    | interval | int | Grouping interval in seconds |
    | collection | PK | PK of the **link** between the classification project and the collection |
    | deployment | list of PKs | Deployments of its resources (sent comma-separated: Trapper reads only one repeated value) |
    | pk | PK | The sequence |

    ``search`` answers ``500`` (Trapper searches a ``name`` that sequences do not have): the SDK warns.
    """

    endpoint = "media_classification/api/sequences"
    schema = Sequence
    known_filters = {"v1": _SEQUENCE_FILTERS, "v2": _SEQUENCE_FILTERS}
    broken_filters = {"search": "answers 500 (it searches a field 'name' that sequences do not have)"}

    def _normalize_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """``deployment`` as Trapper reads it: comma-separated PKs."""
        return self._normalize_lists(query, comma=("deployment",))
