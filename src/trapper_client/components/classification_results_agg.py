"""
Component for the trap rates of a classification project (its results aggregated per deployment and species).
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Dict

from trapper_client import err
from trapper_client.components._classification_filters import ClassificationFiltersMixin
from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import ClassificationAgg, PaginatedResult
from trapper_client._pk import takes_pk
from trapper_client.schemas import ClassificationProject  # noqa: F401  (pk parameters)


class ClassificationResultsAggComponent(ClassificationFiltersMixin, TrapperComponent[ClassificationAgg]):
    """
    The **trap rates** of a classification project (``client.classification_results_agg``).

    - ``GET /media_classification/api/classifications/results/agg/{project_pk}/``: Trapper takes the final
      classifications of the project (the ones the filters keep), adds up the count of each species per deployment
      and divides it by the days the deployment worked. One row per deployment and species, with the deployment's
      Camtrap DP fields: a gzip CSV (``get_project_results_agg``, ``export_project_results_agg``) or, with
      ``geojson=True``, a GeoJSON ``FeatureCollection`` with one point per row (``get_project_geojson``).

    Deployments without start or end date are left out. With no rows Trapper answers ``400 "Empty queryset"``: the
    SDK gives no rows instead.

    **Parameters:**

    | Parameter | Type | Default | Description |
    |---|---|---|---|
    | count_var | ``"count"`` / ``"countNew"`` | ``"count"`` | What is added up. ``countNew`` only if the classificator has it (``400`` otherwise) |
    | all_dep | boolean | ``False`` | Every deployment of the project, also the ones with no observation |
    | filter_dep | text | | Only deployments whose ``deploymentID`` contains it |

    **Filters:** those of the results table of ``client.classification_results`` (``ClassificationFilter``):
    ``approved`` (sent as ``status`` on v1), ``species``, ``observation_type``, ``deployment``, ``collection``,
    ``rdate_from``/``rdate_to``, ``ftype``, ``bboxes``, ... Trapper ignores any other without an error; the SDK emits
    an ``UnknownFilterWarning``. ``classified``/``classified_ai`` answer ``500`` on v2 (warning).
    """

    endpoint = "media_classification/api/classifications/results/agg/{project_pk}/"
    schema = ClassificationAgg
    known_filters = ClassificationFiltersMixin._filters_for(
        frozenset({"count_var", "all_dep", "filter_dep", "geojson", "search"})
    )

    #: Filters the v2 table answers ``500`` to (the annotation only exists in the classification list).
    _BROKEN_ON_V2 = ("classified", "classified_ai")

    def _endpoint_for(self, project_pk: int) -> str:
        return self.endpoint.replace("{project_pk}", str(project_pk))

    def _query(self, query: Dict[str, Any] | None, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        q = dict(self._merge_query(query, kwargs) or {})
        broken = [name for name in self._BROKEN_ON_V2 if name in q]
        if broken and self.client.server_version == "v2":
            warnings.warn(
                f"{self.endpoint}: Trapper v2 answers 500 to {', '.join(repr(b) for b in broken)} (the field only "
                "exists in the classification list)",
                err.UnknownFilterWarning,
                stacklevel=err.user_stacklevel(),
            )
        return q

    @staticmethod
    def _is_geojson(q: Dict[str, Any]) -> bool:
        return str(q.get("geojson", "False")).strip().lower() == "true"

    @takes_pk(project_pk=ClassificationProject)
    def get_project_results_agg(
        self,
        project_pk: int | ClassificationProject,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[ClassificationAgg]:
        """The trap rates of a project: one row per deployment and species.

        Trapper sends the whole table at once: ``page`` and ``page_size`` are not used by it.

        Args:
            project_pk: Classification project primary key.
            query: Base query parameters (filters, ``count_var``, ``all_dep``, ``filter_dep``).
            page: Kept for compatibility.
            page_size: Kept for compatibility.
            validate: Whether to validate each row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            ``PaginatedResult[ClassificationAgg]``; no rows when nothing matches.

        Raises:
            ValueError: With ``geojson=True``: use :meth:`get_project_geojson`.
        """
        q = self._query(query, kwargs)
        if self._is_geojson(q):
            raise ValueError("geojson=True gives a FeatureCollection, not rows: use get_project_geojson()")
        q.setdefault("page", page)
        q.setdefault("page_size", page_size)
        data = self._get_or_empty(self._endpoint_for(project_pk), q)
        return self._to_paginated(data, validate=validate)

    @takes_pk(project_pk=ClassificationProject)
    def get_project_geojson(
        self, project_pk: int | ClassificationProject, query: Dict[str, Any] | None = None, **kwargs: Any,
    ) -> Dict[str, Any]:
        """The trap rates of a project as a GeoJSON ``FeatureCollection``: one point per deployment and species.

        Each feature has the row's fields (without ``latitude`` and ``longitude``) as properties. An empty
        ``FeatureCollection`` when nothing matches.

        Args:
            project_pk: Classification project primary key.
            query: Base query parameters (filters, ``count_var``, ``all_dep``, ``filter_dep``).
            **kwargs: Extra query parameters merged into ``query``.
        """
        q = self._query(query, kwargs)
        q["geojson"] = "True"
        try:
            data = self.client.get(self._endpoint_for(project_pk), query=q)
        except Exception as exc:
            if self._is_empty_result(exc):
                return {"type": "FeatureCollection", "features": []}
            raise
        # The client wraps a JSON object in a one-row envelope.
        results = data.get("results") if isinstance(data, dict) else None
        if isinstance(results, list) and len(results) == 1 and isinstance(results[0], dict):
            return results[0]
        return data

    @takes_pk(project_pk=ClassificationProject)
    def export_project_results_agg(
        self,
        project_pk: int | ClassificationProject,
        query: Dict[str, Any] | None = None,
        file: str | Path | None = None,
        validate: bool = True,
        raw: bool = False,
        **kwargs: Any,
    ) -> Path:
        """Save the trap rates of a project to a CSV.

        Args:
            project_pk: Classification project primary key.
            query: Base query parameters (filters, ``count_var``, ``all_dep``, ``filter_dep``).
            file: Output CSV file path. If ``None``, a temp file is created.
            validate: Parse the rows and write them with the SDK's columns. ``False`` saves Trapper's CSV as it
                comes, like ``raw``.
            raw: Save the CSV exactly as Trapper sends it (its header and column order).
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Path to the CSV (empty when nothing matches).

        Raises:
            ValueError: With ``geojson=True``: use :meth:`get_project_geojson`.
        """
        q = self._query(query, kwargs)
        if self._is_geojson(q):
            raise ValueError(
                "export_project_results_agg only supports CSV export; use get_project_geojson() for GeoJSON"
            )
        endpoint = self._endpoint_for(project_pk)
        if raw or not validate:
            try:
                return self.client.export_all(endpoint, query=q, file=file)
            except Exception as exc:
                if not self._is_empty_result(exc):
                    raise
                output_path = self.client._select_file(file)
                output_path.write_text("")
                return output_path

        data = self._get_all_or_empty(endpoint, q)
        parsed = self._to_paginated(data, validate=True)
        output_path = self.client._select_file(file)
        rows = [item.model_dump(mode="json") for item in parsed.results]
        self.client._write_csv(rows, output_path)
        return output_path
