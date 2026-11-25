"""
Component for classification results data package endpoint.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from trapper_client import err
from trapper_client.components.base import TrapperComponent
from trapper_client.retry_utils import retrying_for_download
from trapper_client.schemas import ResultsDataPackageResponse


#: The parameters Trapper reads (``ResultsDataPackageGeneratorParams``), by version.
_PACKAGE_PARAMS = frozenset({
    "clear_cache", "release", "get_released", "export_format", "export_filetype", "approved_only", "exclude_blank",
    "all_deployments", "filter_deployments", "include_events", "events_count_var", "trapper_url_token",
    "private_human", "private_vehicle", "private_species", "name", "version", "title", "description", "keywords",
    "licenses",
})

#: Parameters Trapper types as a list but reads as one text: they always fail (see ``_UNREADABLE``).
_UNREADABLE = {
    "keywords": "400 \"'a' is not of type 'array'\"",
    "licenses": "400 \"'str' object has no attribute 'name'\"",
    "private_species": "400 \"'is_in' cannot check for List(String) values\"",
}


class ClassificationPackageComponent(TrapperComponent[ResultsDataPackageResponse]):
    """
    The **Camtrap DP data package** of a classification project (``client.classification_package``).

    - ``GET /media_classification/api/package/{project_pk}/``: Trapper builds the package (a zip with
      ``datapackage.json`` and the ``deployments``, ``media`` and ``observations`` tables, plus ``events`` with
      ``include_events``), or takes it from its cache, and answers ``{"data": {"message", "errors", "package"}}``.
      ``package`` is the download URL: it carries its own token (``?rt=...``), works without the API token, and
      stays valid until the package is rebuilt. :meth:`download_package` saves it;
      :meth:`download_project_package` builds and saves it in one call.

    The package is built in the request (seconds for a small project). Trapper caches one per set of
    parameters: ``clear_cache=True`` rebuilds it.

    **Parameters** (Trapper ignores any other without an error; the SDK emits an ``UnknownFilterWarning``):

    | Parameter | Type | Default | Description |
    |---|---|---|---|
    | clear_cache | bool | False | Rebuild instead of reusing the cached package |
    | release | bool | False | Mark the package as a release (see the warning below) |
    | get_released | bool | False | Return the latest release instead (see the warning below) |
    | export_format | str | ``"camtrapdp"`` | Or ``"trapper"`` (Trapper's columns; no events) |
    | export_filetype | str | ``"csv.gz"`` | Or ``"parquet"`` (anything else is a ``400``) |
    | split_custom_attrs | bool | False | **v2**, ``"trapper"`` format: one column per custom attribute (not importable) |
    | approved_only | bool | True | Only approved classifications |
    | exclude_blank | bool | False | Leave out blank observations |
    | all_deployments | bool | True | Every deployment of the project |
    | filter_deployments | str | | Only deployments whose ``deploymentID`` **contains** this text (not PKs) |
    | include_events | bool | False | Add the events (sequences) table |
    | events_count_var | str | ``"count"`` | Count variable of the events table |
    | trapper_url_token, private_human, private_vehicle | bool | True | As in ``classification_media`` |
    | name, version, title, description | str | | Package metadata (``version`` ``"1.0"``) |

    ``keywords``, ``licenses`` and ``private_species`` are lists for Trapper, but it reads one text per parameter and
    always fails on them: the SDK raises a ``ValueError`` instead. The package takes the research project's keywords
    and ``private`` licenses.

    ``release``/``get_released`` do not work together through the API: a release built here is stored as a cached
    package, which ``get_released`` does not look at; and ``get_released=True`` with no release builds a new package
    next to the cached one, after which Trapper answers ``400 "get() returned more than one UserDataPackage"`` for
    those parameters (``clear_cache`` included) until an admin deletes one.

    On **v1** the contributors of the package are the admins of the classification project: a project with no
    admin role fails (``[] should be non-empty at property 'contributors'``).

    Example::

        path = client.classification_package.download_project_package(
            7, "doñana.zip", clear_cache=True, approved_only=False, title="Doñana camera traps 2026",
        )
    """

    endpoint = "media_classification/api/package/{project_pk}/"
    schema = ResultsDataPackageResponse
    known_filters = {"v1": _PACKAGE_PARAMS, "v2": _PACKAGE_PARAMS | {"split_custom_attrs"}}

    def _check_params(self, q: Dict[str, Any]) -> None:
        unreadable = [name for name in _UNREADABLE if name in q]
        if unreadable:
            raise ValueError(
                "Trapper cannot read " + ", ".join(f"{n} (it answers {_UNREADABLE[n]})" for n in unreadable)
                + ": it types them as lists but reads one text per parameter. Leave them out; the package takes "
                "the research project's keywords and 'private' licenses."
            )

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
            )
        """
        q = self._merge_query(query, kwargs)
        self._check_params(q)
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
        detail = f"{message}: {errors}" if errors else message
        if errors and "property 'contributors'" in str(errors):
            detail += (
                " (the contributors of the package are the admins of the classification project: give the project"
                " an admin role)"
            )
        if errors and "returned more than one UserDataPackage" in str(errors):
            detail += (
                " (Trapper has two cached packages for these parameters, usually after get_released=True on a "
                "project with no release; it fails for them until an admin deletes one in Django admin, User data "
                "packages)"
            )
        return detail

    def download_package(
        self,
        package: str | ResultsDataPackageResponse | Dict[str, Any],
        file: str | Path,
        retry_attempts: int = 3,
        retry_min_wait: float = 1.0,
        retry_max_wait: float = 10.0,
    ) -> Path:
        """Save a package Trapper built (the ``package`` URL of :meth:`get_project_package`) to a zip.

        The URL carries its own token, so no login is needed. It is streamed to ``<file>.part`` and moved into
        place; network failures and ``502``/``503``/``504`` answers are retried.

        Args:
            package: The response of :meth:`get_project_package`, or its ``data.package`` URL.
            file: Where to save the zip. An existing directory saves it as ``<package id>.zip``.
            retry_attempts: Attempts in total, the first one included.
            retry_min_wait: Minimum backoff in seconds.
            retry_max_wait: Maximum backoff in seconds.

        Returns:
            The ``Path`` of the zip.

        Raises:
            ValueError: The response has no package URL.
            err.NotFoundError: The URL is no longer valid (the package was rebuilt).
        """
        url = package
        if isinstance(package, ResultsDataPackageResponse):
            url = package.data.package if package.data else None
        elif isinstance(package, dict):
            url = (package.get("data") or {}).get("package")
        if not url:
            raise ValueError("the response has no package URL (data.package): the package was not built")
        target = Path(file)
        if target.is_dir():
            target = target / f"{url.rstrip('/').split('?')[0].rstrip('/').split('/')[-1]}.zip"
        retrying = retrying_for_download(retry_attempts, retry_min_wait, retry_max_wait)
        return retrying(self._download_once, url, target)

    def _download_once(self, url: str, target: Path) -> Path:
        with self.client._client.stream("GET", url) as response:
            status = response.status_code
            if status in (502, 503, 504):
                raise err.TransientDownloadError(f"package: the server answered {status}")
            if status == 404:
                raise err.NotFoundError("package: not found; the URL is no longer valid once the package is rebuilt")
            if status != 200:
                raise err.HTTP_ERRORS_MAP.get(status, err.APIError)(f"package: the server answered {status}")
            if response.headers.get("x-accel-redirect") and response.headers.get("content-length") == "0":
                raise err.APIError(
                    "package: the server answered 200 with no body and an X-Accel-Redirect header: it is not behind "
                    "the proxy that serves Trapper's files, so the package cannot be downloaded"
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            part = target.with_name(target.name + ".part")
            try:
                with part.open("wb") as handle:
                    for chunk in response.iter_bytes():
                        handle.write(chunk)
                part.replace(target)
            except BaseException:
                part.unlink(missing_ok=True)
                raise
        return target

    def download_project_package(
        self, project_pk: int, file: str | Path, query: Dict[str, Any] | None = None, **kwargs: Any,
    ) -> Path:
        """Build (or take from the cache) the package of a project and save it to a zip.

        Args:
            project_pk: Classification project primary key.
            file: Where to save the zip (a directory saves it as ``<package id>.zip``).
            query: Parameters of :meth:`get_project_package`.
            **kwargs: More parameters (``clear_cache=True``, ``approved_only=False``, ...).

        Returns:
            The ``Path`` of the zip.
        """
        response = self.get_project_package(project_pk, query=query, **kwargs)
        return self.download_package(response, file)

