"""
Component for classification results data package endpoint.
"""

from __future__ import annotations

from typing import Any, Dict

from trapper_client import err
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
        raise_on_error: bool = True,
        **kwargs: Any,
    ) -> ResultsDataPackageResponse | Dict[str, Any]:
        """Generate or fetch package metadata and download URL for one project.

        Args:
            project_pk: Classification project primary key.
            query: Base query parameters.
            validate: Whether to validate the payload with Pydantic.
            raise_on_error: Whether to raise mapped API exceptions (e.g. a
                generation failure returned as a 400, or an invalid project).
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            ``ResultsDataPackageResponse`` when ``validate=True``.
            Otherwise, raw dict-like payload from the endpoint.

        Raises:
            err.APIError: If the request fails (a 4xx/5xx response) and
                ``raise_on_error=True``. The exception message includes the
                server's actual ``data.message``/``data.errors`` when the
                response is JSON — but a genuine unhandled server-side
                exception (as opposed to a reported generation failure)
                returns Django's plain HTML error page instead, with no JSON
                body at all; this method detects that case and raises a
                clear error with a text snippet rather than crashing on
                ``response.json()``.

        Example::

            response = client.classification_package.get_project_package(
                project_pk=7,
                clear_cache=True,
                approved_only=False,
                title="Doñana camera traps 2026",
                keywords=["camera-trap", "doñana"],
            )
        """
        q = self._merge_query(query, kwargs)
        endpoint = self.endpoint.replace("{project_pk}", str(project_pk))

        # Use raw request here because APIClientBase.get wraps plain JSON into
        # pagination/results envelope, but this endpoint already has a fixed
        # JSON shape. raise_on_error=False here regardless of the caller's
        # setting: this endpoint's error body is
        # {"data": {"message", "errors", "package"}}, not the
        # {"_error": {"message": ...}} shape APIClientBase._handle_error
        # expects — letting it auto-raise would surface the raw dict repr
        # instead of the server's actual validation message. We parse the
        # real body ourselves below and raise a clean error from it instead.
        response = self.client.make_request(
            endpoint=endpoint, method="GET", query=q, raise_on_error=False,
        )

        if not (200 <= response.status_code < 300):
            if raise_on_error:
                detail = self._error_detail(response)
                error_cls = err.HTTP_ERRORS_MAP.get(response.status_code, err.APIError)
                raise error_cls(
                    f"Classification package request failed (status {response.status_code}): {detail}"
                )
            try:
                return response.json()
            except ValueError:
                return {"data": {"message": response.text[:2000], "errors": None, "package": None}}

        try:
            data = response.json()
        except ValueError as e:
            raise err.APIError(
                f"Classification package request returned status {response.status_code} but "
                f"the response body isn't JSON — this is unexpected for a success status; "
                f"check the server logs. Response snippet: {response.text[:1000]}"
            ) from e

        if validate:
            return ResultsDataPackageResponse.model_validate(data)
        if isinstance(data, dict):
            return ResultsDataPackageResponse.model_construct(**data)
        return data

    def _error_detail(self, response) -> str:
        """Best-effort extraction of an error detail from a failed request.

        The endpoint normally returns JSON (``{"data": {"message", "errors", ...}}``)
        even on failure, but a genuine *unhandled* server-side exception (as
        opposed to a reported generation failure the view catches) bypasses
        that and returns Django's plain HTML error page instead — calling
        ``response.json()`` on that raises ``JSONDecodeError``. This falls
        back to a text snippet in that case so the caller still gets a clear
        error instead of an opaque JSON-parsing traceback.

        Args:
            response: The raw ``httpx.Response`` from the failed request.

        Returns:
            A human-readable detail string.
        """
        try:
            payload = response.json()
        except ValueError:
            return f"non-JSON response (likely an unhandled server error): {response.text[:1000]}"

        block = payload.get("data", {}) if isinstance(payload, dict) else {}
        message = block.get("message") or "Classification package request failed"
        errors = block.get("errors")
        return f"{message}: {errors}" if errors else message

