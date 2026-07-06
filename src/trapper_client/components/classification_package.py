"""
Component for classification results data package endpoint.
"""

from __future__ import annotations

from typing import Any, Dict

from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import ResultsDataPackageResponse


class ClassificationPackageComponent(TrapperComponent[ResultsDataPackageResponse]):
    """
    Component for ``/media_classification/api/package/{project_pk}/``.

    Available endpoints:
    - ``GET /media_classification/api/package/{project_pk}/``

    Returns JSON with ``data.message``, ``data.errors``, and ``data.package``
    (absolute download URL when generation succeeds). That URL already carries
    its own one-time access token (``?rt=...``), so it must be downloaded
    as-is (e.g. via ``client.make_request(endpoint=response.data.package,
    method="GET")``), not re-requested through a component method.

    **Available generation/cache parameters:**

    | Parameter       | Type | Default       | Description                                          |
    |-----------------|------|---------------|-------------------------------------------------------|
    | clear_cache     | bool | False         | Force regeneration instead of reusing the cached package |
    | release         | bool | False         | Mark the generated package as a release                |
    | get_released    | bool | False         | Return the latest already-published release instead    |
    | export_format   | str  | "camtrapdp"   | Also accepts "trapper" (disables ``include_events``)    |
    | export_filetype | str  | "csv.gz"      | File format for the data tables inside the package      |

    **Available content-filtering parameters:**

    | Parameter          | Type | Default | Description                                              |
    |--------------------|------|---------|------------------------------------------------------------|
    | approved_only      | bool | True    | Only include approved classifications                      |
    | exclude_blank      | bool | False   | Exclude blank observations                                  |
    | all_deployments    | bool | True    | Include all deployments of the project                     |
    | filter_deployments | str  | None    | Comma-separated deployment PKs (when ``all_deployments=False``) |
    | include_events     | bool | False   | Include the events/sequences table                          |
    | events_count_var   | str  | "count" | Name of the count variable in the events table              |

    **Available media URL/privacy parameters** (same flags as ``classification_media``):

    | Parameter          | Type | Default |
    |--------------------|------|---------|
    | trapper_url_token  | bool | True    |
    | private_human      | bool | True    |
    | private_vehicle    | bool | True    |
    | private_species    | list | []      |

    **Available package metadata parameters** (written into ``datapackage.json``):

    | Parameter   | Type | Default |
    |-------------|------|---------|
    | name        | str  | None    |
    | version     | str  | "1.0"   |
    | title       | str  | None    |
    | description | str  | None    |
    | keywords    | list | []      |
    | licenses    | list | []      |

    Example::

        response = client.classification_package.get_project_package(
            project_pk=7,
            clear_cache=True,
            approved_only=False,
            title="Doñana camera traps 2026",
            keywords=["camera-trap", "doñana"],
        )
    """

    endpoint = "media_classification/api/package/{project_pk}/"
    schema = ResultsDataPackageResponse

    def get_project_package(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        validate: bool = True,
        **kwargs: Any,
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

