"""
Component for classification results data package endpoint.
"""

from __future__ import annotations

from typing import Any, Dict

from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import ResultsDataPackageResponse


class ClassificationPackageComponent(TrapperComponent[ResultsDataPackageResponse]):
    """
    Component for ``/media_classification/api/package/{project_pk}``.

    Available endpoints:
    - ``GET /media_classification/api/package/{project_pk}``

    Returns JSON with ``data.message``, ``data.errors``, and ``data.package``
    (absolute download URL when generation succeeds).
    """

    endpoint = "media_classification/api/package/{project_pk}"
    schema = ResultsDataPackageResponse

    def get_project_package(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        validate: bool = True,
        **kwargs,
    ) -> ResultsDataPackageResponse | Dict[str, Any]:
        """Generate or fetch package metadata and download URL for one project.

        Args:
            project_pk: Classification project primary key.
            query: Base query parameters.
            validate: Whether to validate the payload with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            ``ResultsDataPackageResponse`` when ``validate=True``.
            Otherwise, raw dict-like payload from the endpoint.
        """
        q = self._merge_query(query, kwargs)
        endpoint = self.endpoint.replace("{project_pk}", str(project_pk))

        # Use raw request here because APIClientBase.get wraps plain JSON into
        # pagination/results envelope, but this endpoint already has a fixed JSON shape.
        response = self.client.make_request(endpoint=endpoint, method="GET", query=q)
        data = response.json()

        if validate:
            return ResultsDataPackageResponse.model_validate(data)
        if isinstance(data, dict):
            return ResultsDataPackageResponse.model_construct(**data)
        return data

