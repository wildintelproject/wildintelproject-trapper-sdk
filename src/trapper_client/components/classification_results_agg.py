"""
Component for aggregated classification results exports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import ClassificationAggRecord, PaginatedResult


class ClassificationResultsAggComponent(TrapperComponent[ClassificationAggRecord]):
    """
    Component for ``/media_classification/api/classifications/results/agg/{project_pk}``.

    Available endpoints:
    - ``GET /media_classification/api/classifications/results/agg/{project_pk}``

    This endpoint returns CSV (gzip) by default, or GeoJSON when ``geojson=True``.
    """

    endpoint = "media_classification/api/classifications/results/agg/{project_pk}"
    schema = ClassificationAggRecord

    def get_project_results_agg(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs,
    ) -> PaginatedResult[ClassificationAggRecord]:
        """Fetch one page of aggregated results for a project.

        Args:
            project_pk: Classification project primary key.
            query: Base query parameters.
            page: Page number to fetch.
            page_size: Number of items per page.
            validate: Whether to validate each row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Paginated result containing ``ClassificationAggRecord`` items.
        """
        q = self._merge_query(query, kwargs)
        q = dict(q or {})
        q.setdefault("page", page)
        q.setdefault("page_size", page_size)

        endpoint = self.endpoint.replace("{project_pk}", str(project_pk))
        data = self.client.get(endpoint, query=q)
        return self._to_paginated(data, validate=validate)

    def export_project_results_agg(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        file: str | Path | None = None,
        validate: bool = True,
        **kwargs,
    ) -> Path:
        """Export aggregated results of one project to CSV.

        Args:
            project_pk: Classification project primary key.
            query: Base query parameters.
            file: Output CSV file path. If ``None``, a temp file is created.
            validate: If ``True``, validates rows before writing CSV.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Path to the generated CSV file.

        Raises:
            ValueError: If ``geojson=True`` is requested, because this method only
                supports CSV export.
        """
        q = self._merge_query(query, kwargs)
        q = dict(q or {})
        if str(q.get("geojson", "False")).lower() == "true":
            raise ValueError("export_project_results_agg only supports CSV export; use get_project_results_agg with geojson=True")

        endpoint = self.endpoint.replace("{project_pk}", str(project_pk))

        if not validate:
            return self.client.export_all(endpoint, query=q, file=file)

        data = self.client.get_all(endpoint, query=q)
        parsed = self._to_paginated(data, validate=True)
        output_path = self.client._select_file(file)
        rows = [item.model_dump(mode="json") for item in parsed.results]
        self.client._write_csv(rows, output_path)
        return output_path

