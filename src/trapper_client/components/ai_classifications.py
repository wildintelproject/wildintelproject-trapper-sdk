"""
Component for AI classifications data endpoint.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from pydantic import BaseModel

from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import AIClassificationRecord, PaginatedResult, AIClassificationRecordExport, \
    AIClassificationRecordExportTrapper, AIClassificationRecordExportCamTrap


class AIClassificationsComponent(TrapperComponent[AIClassificationRecord]):
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
    schema = AIClassificationRecord
    export_schema = AIClassificationRecordExport

    def export(
            self,
            classification_prokect_pk:int,
            query: Dict[str, Any] | None = None,
            file: str | Path | None = None,
            validate: bool = True,
            overwrite_endpoint: str | None = None,
            **kwargs,
    ) -> Path | list[BaseModel]:
        """
        Export resource data as CSV or as a list of parsed models.

        If ``export_endpoint`` is defined on the component, it is used instead of
        ``endpoint`` to fetch the data. This allows components to use a dedicated
        export endpoint (e.g. ``/geomap/api/locations/export/``) when available.

        If ``file`` is provided, results are written to CSV and the path is returned.
        If ``file`` is None, a list of parsed models is returned instead.

        If ``export_schema`` is defined on the component, it is used for parsing;
        otherwise ``schema`` is used as fallback.

        If ``validate`` is False, the raw API export endpoint is used directly
        (only meaningful when ``file`` is provided).

        Args:
            query: Base query parameters.
            file: Output CSV path. If None, returns a list of models.
            validate: Whether to parse results with Pydantic.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``Path`` when ``file`` is provided, otherwise ``list[BaseModel]``.
        """
        endpoint = self.export_endpoint.format(project_pk=classification_prokect_pk)

        q = self._merge_query(query, kwargs)
        if not validate:
            return self.client.export_all(endpoint, query=q, file=file)

        raw_data = self.client.get_all(endpoint, query=q)
        rows_raw = raw_data.get("results", [])

        items = [self._validate_ai_export_record(row) for row in rows_raw]

        if file is None:
            return items

        output_path = self.client._select_file(file)
        rows = [item.model_dump(mode="json") for item in items]
        self.client._write_csv(rows, output_path)
        return output_path


        """return super().export(
            query=query,
            file=file,
            validate=validate,
            overwrite_endpoint= endpoint,
            **kwargs,
        )"""

    def _validate_ai_export_record(self,row: dict):
        row = self._clean_row(row)
        if "_id" in row:
            return AIClassificationRecordExportTrapper.model_validate(row)
        else:
            return AIClassificationRecordExportCamTrap.model_validate(row)

    def _clean_row(self,row: dict) -> dict:
        return {
            k: (None if v == "" else v)
            for k, v in row.items()
        }