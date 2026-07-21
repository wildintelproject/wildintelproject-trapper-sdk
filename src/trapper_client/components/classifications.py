"""
Component for classification observations exports.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Union

from tenacity import Retrying

from trapper_client import err
from trapper_client.api_query import APIQuery
from trapper_client.components.base import TrapperComponent
from trapper_client.csv_chunking import DEFAULT_MAX_CHUNK_BYTES, split_csv_by_size
from trapper_client.retry_utils import retrying_for_chunk_upload
from trapper_client.schemas import (
    ClassificationImportResponse,
    ClassificationRecord,
    ClassificationRecordExport,
    PaginatedResult,
)


class ClassificationsComponent(TrapperComponent[ClassificationRecord]):
    """
    Component for ``/media_classification/api/classifications``.

    Main endpoints:
    - ``GET /media_classification/api/classifications``: List of AI classifications (paginated)
    - ``GET /media_classification/api/classifications/{pk}	``: Single AI classification detail
    - ``GET /media_classification/api/classifications/results/{project_pk}/	``: CSV con resultados AI de un proyecto
    - ``POST /media_classification/api/classifications/import/``: importa observaciones expertas/AI desde un CSV

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
            **kwargs: Any,
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
            overwrite_schema=self.export_schema,
            **kwargs,
        )

    def where_project_results(
            self,
            project_pk: int,
            query: Dict[str, Any] | None = None,
            page_size: int = 50,
            validate: bool = True,
            **kwargs: Any,
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
            overwrite_schema=self.export_schema,
            **kwargs,
        )

    def export_project_results(
            self,
            project_pk: int,
            query: Dict[str, Any] | None = None,
            file: str | Path | None = None,
            validate: bool = True,
            **kwargs: Any,
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

    def import_classifications(
            self,
            project_id: int,
            file: str | Path,
            approve: bool = True,
            import_bboxes: bool = True,
            import_expert_classifications: bool = True,
            import_ai_classifications: bool = False,
            overwrite_attrs: bool = False,
            ai_provider_id: int | str | None = None,
            validate: bool = True,
            split: bool = False,
            delay: float = 1.0,
            chunk_size: int = DEFAULT_MAX_CHUNK_BYTES,
            retry_attempts: int = 3,
            retry_min_wait: float = 1.0,
            retry_max_wait: float = 10.0,
            raise_on_error: bool = True,
    ) -> Union[
        ClassificationImportResponse, Dict[str, Any],
        List[Union[ClassificationImportResponse, Dict[str, Any]]],
    ]:
        """Import expert/AI observations from a CSV file into a classification project.

        Posts to ``media_classification/api/classifications/import/``. The CSV
        must follow the internal Trapper format and contain an ``_id`` column.
        Depending on server configuration the import runs synchronously or is
        scheduled as a Celery task, in which case the response carries a
        ``task_id`` instead of a final result message.

        Args:
            project_id: Classification project primary key.
            file: Path to the observations CSV file to upload.
            approve: Mark imported classifications as approved.
            import_bboxes: Import bounding boxes present in the ``bboxes`` column.
            import_expert_classifications: Import rows with classificationMethod = human.
            import_ai_classifications: Import rows with classificationMethod = machine.
                Requires ``ai_provider_id``.
            overwrite_attrs: Overwrite existing classification attributes when
                approving imported AI classifications.
            ai_provider_id: AI provider primary key. Required when
                ``import_ai_classifications=True``.
            validate: Whether to validate the response with Pydantic.
            split: Instead of uploading ``file`` in one request, split it into
                several smaller, self-contained CSV chunks (each repeating the
                header row) and import them one request at a time, sleeping
                ``delay`` seconds between uploads. Unlike
                :meth:`~trapper_client.components.locations.LocationsComponent.import_locations`,
                this endpoint is a real REST API that can usually take a full
                file in one request — this is only useful as a workaround for
                very large CSVs that hit request-size limits (this server's
                ``DATA_UPLOAD_MAX_MEMORY_SIZE``/reverse-proxy limits) or time
                out. There is no real chunked/resumable upload protocol here
                (see :mod:`trapper_client.csv_chunking`).
            delay: Seconds to sleep between chunk uploads when ``split=True``.
                Ignored otherwise.
            chunk_size: Maximum size in bytes of each chunk when ``split=True``.
                Ignored otherwise. Defaults to 512 KiB.
            retry_attempts: Maximum number of attempts (first try + retries)
                per chunk/file upload when the request fails with a
                network-level error (read timeout, connection reset, ...) —
                the failure mode expected when a chunk is still too large or
                slow for the server. Does not retry on HTTP error responses
                (those are validation failures a retry can't fix). Set to
                ``1`` to disable retrying.
            retry_min_wait: Minimum exponential backoff delay in seconds
                between retry attempts.
            retry_max_wait: Maximum exponential backoff delay in seconds
                between retry attempts.
            raise_on_error: Whether to raise mapped API exceptions (e.g. missing
                project/AI provider, or invalid CSV rows returned as a 400).
                With ``split=True``, raises as soon as one chunk fails rather
                than uploading the rest.

        Returns:
            ``ClassificationImportResponse`` when ``validate=True``, otherwise
            the raw response dict. When ``split=True``, a list with one such
            result per chunk (in file order) instead of a single result.

        Raises:
            ValueError: If ``import_ai_classifications=True`` but ``ai_provider_id`` is not set.
            err.APIError: If the import fails (a 4xx/5xx response) and
                ``raise_on_error=True``. The exception message includes the
                server's actual ``data.message``/``data.errors`` (e.g. Django
                form errors per field) when the response is JSON — but a
                genuine unhandled server-side exception (as opposed to a
                validation failure) returns Django's plain HTML error page
                instead, with no JSON body at all; this method detects that
                case and raises a clear error with a text snippet rather than
                crashing on ``response.json()``.

        Example::

            result = client.classification_results.import_classifications(
                project_id=7, file="/tmp/observations.csv",
            )
            print(result.data.message, result.data.task_id)

            # A very large CSV, uploaded in <=512 KiB chunks, 2s apart:
            results = client.classification_results.import_classifications(
                project_id=7, file="/tmp/huge_observations.csv",
                split=True, delay=2,
            )
        """
        if import_ai_classifications and ai_provider_id is None:
            raise ValueError("ai_provider_id is required when import_ai_classifications=True")

        data: Dict[str, Any] = {
            "project_id": project_id,
            "approve": approve,
            "import_bboxes": import_bboxes,
            "import_expert_classifications": import_expert_classifications,
            "overwrite_attrs": overwrite_attrs,
        }
        if import_ai_classifications:
            # Sent only when True: the server reads this flag from the raw
            # request body *before* running it through form validation, as a
            # plain Python truthy check — a literal "False" string sent over
            # multipart would still be truthy there.
            data["import_ai_classifications"] = True
            data["ai_provider_id"] = ai_provider_id

        retrying = retrying_for_chunk_upload(retry_attempts, retry_min_wait, retry_max_wait)

        if not split:
            return self._import_classifications_once(data, Path(file), validate, raise_on_error, retrying)

        chunk_paths = split_csv_by_size(file, max_bytes=chunk_size)
        try:
            results = []
            for i, chunk_path in enumerate(chunk_paths):
                results.append(
                    self._import_classifications_once(data, chunk_path, validate, raise_on_error, retrying)
                )
                if i < len(chunk_paths) - 1:
                    time.sleep(delay)
            return results
        finally:
            for chunk_path in chunk_paths:
                chunk_path.unlink(missing_ok=True)

    def _import_classifications_once(
            self,
            data: Dict[str, Any],
            file_path: Path,
            validate: bool,
            raise_on_error: bool,
            retrying: Retrying,
    ) -> ClassificationImportResponse | Dict[str, Any]:
        """Perform one ``media_classification/api/classifications/import/`` POST for a single CSV file."""
        endpoint = f"{self.endpoint.rstrip('/')}/import/"
        with file_path.open("rb") as fh:
            def _do_request():
                # Rewind before every attempt: a retry re-sends the same file
                # object, whose read position may have advanced past a
                # partial read from a prior attempt that timed out mid-upload.
                fh.seek(0)
                # raise_on_error=False here regardless of the caller's setting: this
                # endpoint's error body is {"data": {"message", "errors", "task_id"}},
                # not the {"_error": {"message": ...}} shape APIClientBase._handle_error
                # expects — letting it auto-raise would surface the raw dict repr
                # instead of the server's actual validation message. We parse the
                # real body ourselves below and raise a clean error from it instead.
                return self.client.post_multipart(
                    endpoint=endpoint,
                    data=data,
                    files={"file": (file_path.name, fh, "text/csv")},
                    raise_on_error=False,
                )

            response = retrying(_do_request)

        if not (200 <= response.status_code < 300):
            if raise_on_error:
                detail = self._import_error_detail(response)
                error_cls = err.HTTP_ERRORS_MAP.get(response.status_code, err.APIError)
                raise error_cls(f"Classification import failed (status {response.status_code}): {detail}")
            try:
                return response.json()
            except ValueError:
                return {"data": {"message": response.text[:2000], "errors": None, "task_id": None}}

        try:
            payload = response.json()
        except ValueError as e:
            raise err.APIError(
                f"Classification import returned status {response.status_code} but the "
                f"response body isn't JSON — this is unexpected for a success status; check "
                f"the server logs. Response snippet: {response.text[:1000]}"
            ) from e

        if validate:
            return ClassificationImportResponse.model_validate(payload)
        return payload

    def _import_error_detail(self, response) -> str:
        """Best-effort extraction of an error detail from a failed import response.

        The endpoint normally returns JSON (``{"data": {"message", "errors", ...}}``)
        even on failure, but a genuine *unhandled* server-side exception (as
        opposed to a validation failure the view catches) bypasses that and
        returns Django's plain HTML error page instead — calling
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
        message = block.get("message") or "Classification import failed"
        errors = block.get("errors")
        return f"{message}: {errors}" if errors else message