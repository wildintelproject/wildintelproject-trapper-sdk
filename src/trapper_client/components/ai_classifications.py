"""
Component for AI classifications data endpoint.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from trapper_client import err
from trapper_client.components._classification_filters import camtrapdp_param
from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import AIClassification, AIClassificationRecordExport


class AIClassificationsComponent(TrapperComponent[AIClassification]):
    """
    Component for ``/media_classification/api/ai-classifications/``.

    Retrieve, filter, and export ai classifications data from Trapper.

    Main endpoints:
    - ``GET /media_classification/api/ai-classifications``: List of AI classifications (paginated)
    - ``GET /media_classification/api/ai-classifications/{pk}	``: Single AI classification detail
    - ``GET /media_classification/api/ai-classifications/results/{project_pk}/	``: CSV con resultados AI de un proyecto

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
    | bboxes         | boolean                  | Has bounding boxes                                                         |
    | user           | list of PKs              | Filter by owner user PKs                                                   |
    | approved       | boolean                  | Whether classification is FINAL approved                                   |
    | feedback       | boolean                  | Whether it is a feedback classification                                    |
    | species        | list of PKs              | Filter by species PKs                                                      |
    | observation_type | choice                 | Filter by observation type                                                 |
    | sex            | choice                   | Filter by sex                                                              |
    | age            | choice                   | Filter by age                                                              |
    | confidence     | number                   | dynamic_attrs.classification_confidence >= value                          |
    | ai_provider    | list of PKs              | Filter by AI provider PKs (choices from AIProvider)                       |

    **Additional fields:**

    | Parameter        | Type                     | Description                                                                 |
    |----------------|--------------------------|-----------------------------------------------------------------------------|
    | camtrapdp      | boolean                  | Format of output: True = Camtrap DP standard, False = Trapper internal format (default: True) |

    Returns a paginated list of AI classifications with support for filtering
    through query parameters.
    """

    endpoint = "/media_classification/api/ai-classifications"
    export_endpoint = "/media_classification/api/ai-classifications/results/{project_pk}/"
    schema = AIClassification
    export_schema = AIClassificationRecordExport

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
