"""
Component for the AI classifications of Trapper.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Dict

from trapper_client import err
from trapper_client.components._classification_filters import RequireProjectMixin, camtrapdp_param
from trapper_client.components.base import TrapperComponent
from trapper_client.components.user_classifications import _LIST_COMMON
from trapper_client.schemas import AIClassification, AIClassificationRecordExport


#: The filters each Trapper version applies to the AI list and to the AI results table (``AIClassificationFilter``).
AI_CLASSIFICATION_FILTERS = {
    "v1": _LIST_COMMON | {"confidence", "ai_provider", "camtrapdp"},
    "v2": _LIST_COMMON | {
        "confidence", "ai_provider", "camtrapdp", "owner", "user", "feedback", "locations_map", "rdate_from",
        "rdate_to", "rtime_from", "rtime_to", "sex", "age", "classified", "classified_ai", "observation_level",
        "avg_confidence_min", "avg_confidence_max",
    },
}


class AIClassificationsComponent(RequireProjectMixin, TrapperComponent[AIClassification]):
    """
    The classifications an AI model made (``client.ai_classifications``), before one is approved as the final one.

    - ``GET /media_classification/api/ai-classifications`` (and ``/{pk}``): the **list**, one row per AI
      classification the user can see. Trapper v2 does not send ``owner``, ``classification`` or ``created_at``.
    - ``GET /media_classification/api/ai-classifications/results/{project_pk}/``: the **AI results table** of a
      project, one row per observation, with the columns of the results table of ``client.classification_results``
      (``export``). ``camtrapdp=False`` gives Trapper's format (with ``_id`` and ``bboxes``).

    The confidence of an observation (``classification_confidence``) is a fraction (``"0.93"``) on both versions,
    the scale of the ``confidence`` filter.

    **Filters** of the list and the table (Trapper ignores any other without an error; the SDK emits an
    ``UnknownFilterWarning``):

    | Parameter | Type | Version | Description |
    |---|---|---|---|
    | project | PK | both | Classification project. **Needed for deployment and collection** (``ValueError`` without it) |
    | deployment | list of PKs | both | Deployment PKs of the project |
    | collection | list of PKs | both | PK of the **link** between the project and the collection |
    | ai_provider | list of PKs | both | AI provider (model) PKs |
    | confidence | number 0-1 | both | Some observation has at least this confidence |
    | approved | boolean | both | It became the final classification. **v2: the table answers 500** (warning) |
    | bboxes | boolean | both | Has bounding boxes |
    | ftype | choice | both | Resource type (I, V, ...) |
    | species | list of PKs | both | Species PKs |
    | observation_type | choice | both | Observation type |
    | search | text | both | Species (Latin or English name), resource name or attribute (list only) |
    | owner, user, feedback | | v2 | As in the user list |
    | locations_map, rdate_from/rdate_to, rtime_from/rtime_to | | v2 | Location, date and time of the resource |
    | sex, age, classified, classified_ai | | v2 | As in the user list |

    v1 also applies one filter per custom attribute of the project's classificator, when ``project`` is given.

    **Extra parameter of the table:** ``camtrapdp`` (default ``True``): ``True`` = Camtrap DP rows, ``False`` =
    Trapper's format.
    """

    endpoint = "/media_classification/api/ai-classifications"
    export_endpoint = "/media_classification/api/ai-classifications/results/{project_pk}/"
    schema = AIClassification
    export_schema = AIClassificationRecordExport
    known_filters = AI_CLASSIFICATION_FILTERS
    unknown_filter_hint = "; or the name of an attribute of the project's classificator (v1, with project)"
    project_hint = "or use export(<project pk>) (the project is in its URL)"

    def _normalize_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """``camtrapdp=True`` as Trapper reads it (``"True"``)."""
        return camtrapdp_param(query)

    def _is_empty_result(self, exc: Exception) -> bool:
        """The results table answers ``400 "Empty queryset ..."`` when no row matches (or with no permission)."""
        return isinstance(exc, err.BadRequestError) and "Empty queryset" in str(exc)

    def export(
            self,
            classification_project_pk: int,
            query: Dict[str, Any] | None = None,
            file: str | Path | None = None,
            validate: bool = True,
            raw: bool = False,
            **kwargs: Any,
    ) -> Path | list[AIClassificationRecordExport]:
        """Export the AI results table of a project (one row per observation) to a list or a CSV.

        The rows are read like the results table of ``client.classification_results``: Camtrap DP rows by default,
        Trapper rows (with ``_id``) with ``camtrapdp=False``. A project with no AI classifications (or none that
        match the filters) gives no rows: ``[]``, or an empty file.

        Args:
            classification_project_pk: Classification project primary key.
            query: Base query parameters (filters, ``camtrapdp``).
            file: Output CSV path. If ``None``, returns a list of rows.
            validate: Whether to parse the rows. ``False`` saves Trapper's CSV as it comes, like ``raw``.
            raw: Save the CSV exactly as Trapper sends it. Needs ``file``.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``Path`` when ``file`` is provided, otherwise a list of
            ``AIClassificationRecordExportCamTrap`` / ``AIClassificationRecordExportTrapper``.
        """
        endpoint = self.export_endpoint.format(project_pk=classification_project_pk)
        if "approved" in {**(query or {}), **kwargs} and self.client.server_version == "v2":
            warnings.warn(
                f"{self.export_endpoint}: Trapper v2 answers 500 to 'approved' in the AI results table "
                "(the field only exists in the list); filter the list instead",
                err.UnknownFilterWarning,
                stacklevel=2,
            )
        if not validate and not raw:
            # validate=False has always saved Trapper's CSV (to a default file when none was given): kept.
            q = self._merge_query(query, kwargs)
            try:
                return self.client.export_all(endpoint, query=q, file=file)
            except Exception as exc:
                if not self._is_empty_result(exc):
                    raise
                output_path = self.client._select_file(file)
                output_path.write_text("")
                return output_path
        return super().export(
            query=query, file=file, validate=validate, raw=raw, overwrite_endpoint=endpoint, **kwargs,
        )
