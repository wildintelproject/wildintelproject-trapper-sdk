"""
Component for classification observations exports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from trapper_client.api_query import APIQuery
from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import ClassificationRecordExport, PaginatedResult, ClassificationRecord, \
    ClassificationRecordExport


class ClassificationsComponent(TrapperComponent[ClassificationRecord]):
    """
    Component for ``/media_classification/api/classifications``.

    Main endpoints:
    - ``GET /media_classification/api/classifications``: List of AI classifications (paginated)
    - ``GET /media_classification/api/classifications/{pk}	``: Single AI classification detail
    - ``GET /media_classification/api/classifications/results/{project_pk}/	``: CSV con resultados AI de un proyecto

    **Available filter fields:**

    | Parameter          | Type                | Description |
    |--------------------|---------------------|-------------|
    | project            | PK                  | Auto-filtrado por URL (no necesario) |
    | owner              | boolean             | true = resources where user is owner/manager |
    | deployment         | list of PKs         | Filter by deployment PKs |
    | collection         | list of PKs         | Filter by collection PKs |
    | locations_map      | comma-separated PKs | Filter by location PKs |
    | rdate_from / rdate_to | date            | date_recorded range |
    | rtime_from / rtime_to | HH:MM           | Time-of-day range |
    | ftype              | choice              | Resource type (IMAGE, VIDEO, etc.) |
    | bboxes             | boolean             | Has bounding boxes |
    | user               | list of PKs         | Filter by owner user PKs |
    | approved           | boolean             | Has FINAL approved classification |
    | feedback           | boolean             | Is feedback classification |
    | species            | list of PKs         | Filter by species PKs |
    | observation_type   | choice              | Filter by observation type |
    | sex                | choice              | Filter by sex |
    | age                | choice              | Filter by age |
    | confidence         | number              | dynamic_attrs.classification_confidence >= value |
    | ai_provider        | list of PKs         | Filter by AI provider PKs (choices from AIProvider) |

    **Additional fields:**

    | Parameter        | Type                     | Description                                                                 |
    |----------------|--------------------------|-----------------------------------------------------------------------------|
    | camtrapdp      | boolean                  | Format of output: True = Camtrap DP standard, False = Trapper internal format (default: True) |


    This endpoint returns observations as CSV (gzip) and supports filters from
    ``ClassificationFilter``.
    """

    endpoint = "/media_classification/api/classifications"
    export_endpoint = "/media_classification/api/classifications/results/{project_pk}/"
    schema = ClassificationRecord
    export_schema = ClassificationRecordExport

    def _resolve_export_endpoint(self, project_pk: int) -> str:
        """Build the export endpoint for a given project pk."""
        return self.export_endpoint.format(project_pk=project_pk)

    def get_project_results(
            self,
            project_pk: int,
            query: Dict[str, Any] | None = None,
            page: int = 1,
            page_size: int = 50,
            validate: bool = True,
            **kwargs,
    ) -> PaginatedResult[ClassificationRecordExport]:
        """Fetch one page of observation rows for a classification project.

        Args:
            project_pk: Classification project primary key.
            query: Base query parameters.
            page: Page number to fetch.
            page_size: Number of items per page.
            validate: Whether to validate each row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Paginated result containing ``ClassificationResultRecord`` items.
        """
        return self.get(
            query=query,
            page=page,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._resolve_export_endpoint(project_pk),
            **kwargs,
        )

    def where_project_results(
            self,
            project_pk: int,
            query: Dict[str, Any] | None = None,
            page_size: int = 50,
            validate: bool = True,
            **kwargs,
    ) -> APIQuery[ClassificationRecordExport]:
        """Return a lazy iterator over observation rows for a project.

        Args:
            project_pk: Classification project primary key.
            query: Base query parameters.
            page_size: Number of items requested per API page.
            validate: Whether to validate each row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Lazy ``APIQuery[ClassificationResultRecord]`` iterator.
        """
        return self.where(
            query=query,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._resolve_export_endpoint(project_pk),
            **kwargs,
        )

    def export_project_results(
            self,
            project_pk: int,
            query: Dict[str, Any] | None = None,
            file: str | Path | None = None,
            validate: bool = True,
            **kwargs,
    ) -> Path | list[ClassificationRecordExport]:
        """Export observation rows for one project to CSV or model list.

        Args:
            project_pk: Classification project primary key.
            query: Base query parameters.
            file: Output CSV file path. If ``None``, returns a list of models.
            validate: Whether to validate rows with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            ``Path`` when ``file`` is provided, otherwise ``list[BaseModel]``.
        """
        return self.export(
            query=query,
            file=file,
            validate=validate,
            overwrite_endpoint=self._resolve_export_endpoint(project_pk),
            **kwargs,
        )