"""
Component for the /storage/api/resources/ resource.
"""

from __future__ import annotations

import mimetypes
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Literal

import httpx

from trapper_client import err
from trapper_client.components.base import TrapperComponent, versioned
from trapper_client.retry_utils import retrying_for_download
from trapper_client.schemas import PaginatedResult, Resource
from trapper_client.api_query import APIQuery
from trapper_client._pk import takes_pk
from trapper_client.schemas import ClassifiedResource, Collection, Location, Resource  # noqa: F401  (pk parameters)


@dataclass
class DownloadReport:
    """What a :meth:`~ResourcesComponent.download_many` run did, file by file.

    Attributes:
        downloaded: Paths written in this run.
        skipped: Paths that were already there (``skip_existing``).
        failed: ``{resource pk: message}`` for the files that could not be downloaded.
        directory: Where the files went.
    """

    directory: Path
    downloaded: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)
    failed: dict[int, str] = field(default_factory=dict)

    @property
    def total(self) -> int:
        """How many resources were looked at."""
        return len(self.downloaded) + len(self.skipped) + len(self.failed)

    @property
    def ok(self) -> bool:
        """``True`` when no file failed."""
        return not self.failed

    def __str__(self) -> str:
        return (f"{len(self.downloaded)} downloaded, {len(self.skipped)} already there, "
                f"{len(self.failed)} failed, in {self.directory}")


_UNSAFE = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')


def safe_filename(name: str, fallback: str = "resource") -> str:
    """A name that is safe as a file name: no path separators or characters Windows refuses, no dot-only names."""
    cleaned = _UNSAFE.sub("_", str(name or "")).strip(" .")
    return cleaned or fallback


class ResourcesComponent(TrapperComponent[Resource]):
    """
    Component for the ``/storage/api/resources`` endpoint.

    Retrieve, filter, and export resource data from Trapper.

    **Main endpoints:**

    - ``GET /storage/api/resources``: Paginated resource list
    - ``GET /storage/api/resources/{pk}``: Single resource
    - ``GET /storage/api/resources/collection/{collection_pk}``: Resources by collection
    - ``GET /storage/api/resources/collection/{collection_pk}/{id}``: Single resource within a collection
    - ``GET /storage/api/resources/location/{location_pk}``: Resources by location
    - ``GET /storage/api/resources/location/{location_pk}/{id}``: Single resource at a location

    **Available filter parameters:**

    +----------------------------+-----------------------------+--------------------------------------------------------------+
    | Parameter                  | Type                        | Description                                                  |
    +============================+=============================+==============================================================+
    | ``pk``                     | comma-separated PKs         | Filter by specific resource PKs                              |
    +----------------------------+-----------------------------+--------------------------------------------------------------+
    | ``resource_type``          | choice                      | Filter by resource type                                      |
    +----------------------------+-----------------------------+--------------------------------------------------------------+
    | ``status``                 | choice                      | Filter by resource status                                    |
    +----------------------------+-----------------------------+--------------------------------------------------------------+
    | ``rdate_from``, ``rdate_to``| date                       | ``date_recorded`` range                                      |
    +----------------------------+-----------------------------+--------------------------------------------------------------+
    | ``udate_from``, ``udate_to``| date                       | ``date_uploaded`` range                                      |
    +----------------------------+-----------------------------+--------------------------------------------------------------+
    | ``rtime_from``, ``rtime_to``| HH:MM                      | Time-of-day range on ``date_recorded``                       |
    +----------------------------+-----------------------------+--------------------------------------------------------------+
    | ``owner``                  | boolean                     | ``true`` = only resources owned/managed by current user      |
    +----------------------------+-----------------------------+--------------------------------------------------------------+
    | ``locations_map``          | list of PKs                 | Filter via ``deployment__location`` (v1 only)                |
    +----------------------------+-----------------------------+--------------------------------------------------------------+
    | ``collections``            | list of PKs                 | Filter by one or more collection PKs                         |
    +----------------------------+-----------------------------+--------------------------------------------------------------+
    | ``deployments``            | repeatable PKs              | Filter by deployment PKs                                     |
    +----------------------------+-----------------------------+--------------------------------------------------------------+
    | ``tags``                   | list of PKs                 | Filter by tag PKs                                            |
    +----------------------------+-----------------------------+--------------------------------------------------------------+
    | ``observation_type``       | string                      | Full-text search for ``observation_type:<value>``            |
    +----------------------------+-----------------------------+--------------------------------------------------------------+
    | ``species``                | repeatable                  | Full-text search for ``species_id:<value>``                  |
    +----------------------------+-----------------------------+--------------------------------------------------------------+
    | ``timestamp_error``        | boolean                     | ``true`` = resources outside deployment's date range         |
    +----------------------------+-----------------------------+--------------------------------------------------------------+
    | ``search``                 | string                      | Full-text search across name and data vectors                |
    +----------------------------+-----------------------------+--------------------------------------------------------------+

    The lists (``pk``, ``locations_map``, ``collections``, ``deployments``, ``tags``, ``species``) can be a list
    or a comma-separated string; the SDK sends each one the way Trapper reads it. A parameter Trapper does not
    apply is ignored by the server, and the SDK warns (:class:`~trapper_client.err.UnknownFilterWarning`).
    ``deployment__isnull`` makes Trapper answer ``500``: it is not a usable filter.

    **Examples:**

    Lazy iteration with filters::

        for res in client.resources.where(status="Public", deployments=12):
            print(res)

    Single page::

        page = client.resources.get(page=1, page_size=100, resource_type="I")

    Single item::

        item = client.resources.find(123)

    All resources by collection (lazy)::

        for res in client.resources.where_by_collection(collection_pk=5):
            print(res)

    All resources by location (lazy)::

        for res in client.resources.where_by_location(location_pk=42):
            print(res)

    Single resource within a collection::

        res = client.resources.find_by_collection(collection_pk=5, resource_pk=123)

    Export all resources to CSV::

        client.resources.export(file="/tmp/resources.csv", status="Public")
    """

    endpoint = versioned("storage/api/resources", ninja="api/v2/resources/")
    #: Ordered by a key that is not unique on the old routes (issue #132).
    unstable_order = True
    schema = Resource

    # What each version applies (checked live on v1 and v2): a parameter that is not here is ignored.
    _COMMON_FILTERS = frozenset({
        "pk", "resource_type", "status", "rdate_from", "rdate_to", "udate_from", "udate_to", "rtime_from",
        "rtime_to", "owner", "collections", "deployments", "tags", "observation_type", "species",
        "timestamp_error", "search", "name", "deployment", "mime_type", "file_size", "token",
        "file_checksum_hash",
    })
    known_filters = {
        "v1": _COMMON_FILTERS | {"locations_map"},
        "v2": _COMMON_FILTERS,       # v2 ignores locations_map: it has no maps
    }
    broken_filters = {"deployment__isnull": "answers 500 (a server error) whatever the value"}

    #: Filters that Trapper reads from repeated parameters (``collections=2&collections=3``) ...
    _REPEATED_FILTERS = frozenset({"collections", "deployments", "tags", "species"})
    #: ... and the ones it reads from one comma-separated string (``pk=1,2,3``).
    _COMMA_FILTERS = frozenset({"pk", "locations_map"})

    def _normalize_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Send the list filters the way Trapper reads each one, whichever way the caller gave them.

        ``deployments="1,2"`` is ignored by Trapper (every resource comes back), ``collections="2,3"`` is a
        400, ``pk=[1, 2]`` keeps one pk and ``locations_map=[1, 2]`` finds nothing; the opposite forms work.
        A list, a tuple, a set or a comma-separated string is accepted for all of them.
        """
        return self._normalize_lists(query, repeated=self._REPEATED_FILTERS, comma=self._COMMA_FILTERS)

    #: The web view that serves the files of a resource (not part of the REST API: it needs a web session).
    media_endpoint = "storage/resource/media/{pk}/{field}/"
    #: What each ``kind`` of :meth:`download` is called in that view.
    media_fields = {"original": "file", "preview": "pfile", "thumbnail": "tfile"}

    @takes_pk(pk=(Resource, ClassifiedResource,))
    def download(
        self,
        pk: int | Resource | ClassifiedResource,
        file: str | Path,
        kind: Literal["original", "preview", "thumbnail"] = "original",
        retry_attempts: int = 3,
        retry_min_wait: float = 1.0,
        retry_max_wait: float = 10.0,
    ) -> Path:
        """Save the file of a resource (its image or video) to disk.

        The REST API only lists resources: ``url`` and ``url_original`` are paths of a classic web view that
        does not accept the API token, and that answers ``404`` both when the file does not exist and when
        the account has no permission to see it. So this logs in with ``user_name``/``user_password`` (the
        account's *email* on servers that log in by email) like the imports do, and streams the file to disk.
        Network failures and ``502``/``503``/``504`` answers are retried with exponential backoff (tenacity);
        any other answer is an error. The file is written to a temporary ``.part`` file first, so a failed
        download never leaves a half-written file where ``file`` should be.

        Warning:
            Not a stable API contract: it depends on an unversioned web view (``storage/resource/media/``).

        Args:
            pk: Resource primary key.
            file: Where to save it. If it is an existing directory, the file is saved in it as
                ``<pk>-<kind>`` plus the extension of its content type.
            kind: ``"original"`` (the file as it was uploaded), ``"preview"`` or ``"thumbnail"``. Trapper
                generates the last two, and a resource may not have them.
            retry_attempts: Attempts in total, the first one included (``1`` disables the retries).
            retry_min_wait: Minimum backoff in seconds.
            retry_max_wait: Maximum backoff in seconds.

        Returns:
            The ``Path`` of the saved file.

        Raises:
            ValueError: If ``kind`` is not one of the three, or ``user_name``/``user_password`` are missing.
            err.NotFoundError: The file does not exist, or the account cannot see the resource.
            err.APIError: Any other failure, including a server that answers ``200`` with an empty body and
                an ``X-Accel-Redirect`` header, which is a Trapper that is not behind the proxy that serves
                its files.

        Example::

            path = client.resources.download(29, "images/")                    # the original
            thumb = client.resources.download(29, "thumb.jpg", kind="thumbnail")
        """
        if kind not in self.media_fields:
            raise ValueError(f"kind must be one of {', '.join(self.media_fields)}, not {kind!r}")
        self._ensure_supported()
        self.client.session_login()

        url = f"{self.client.base_url.rstrip('/')}/{self.media_endpoint.format(pk=pk, field=self.media_fields[kind])}"
        retrying = retrying_for_download(retry_attempts, retry_min_wait, retry_max_wait)
        return retrying(self._download_once, url, pk, kind, Path(file))

    def _download_once(self, url: str, pk: int, kind: str, target: Path) -> Path:
        """One attempt at :meth:`download`: stream to ``<target>.part`` and move it into place."""
        with self.client._web_client.stream("GET", url) as response:
            status = response.status_code
            if status != 200:
                self._raise_download_error(response, pk, kind)
            if response.headers.get("x-accel-redirect") and response.headers.get("content-length") == "0":
                raise err.APIError(
                    f"resource {pk}: the server answered 200 with no body and an X-Accel-Redirect header: "
                    "it is not behind the proxy that serves Trapper's files, so the file cannot be downloaded"
                )
            if target.is_dir():
                extension = mimetypes.guess_extension((response.headers.get("content-type") or "").split(";")[0].strip()) or ""
                target = target / f"{pk}-{kind}{'.jpg' if extension == '.jpe' else extension}"
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

    @staticmethod
    def _raise_download_error(response: httpx.Response, pk: int, kind: str) -> None:
        status = response.status_code
        if status in (502, 503, 504):
            raise err.TransientDownloadError(f"resource {pk}: the server answered {status}")
        if status == 404:
            raise err.NotFoundError(
                f"resource {pk} ({kind}): not found. The file does not exist (a preview or thumbnail may not "
                "have been generated), or the account has no permission to see the resource: Trapper answers "
                "404 in both cases"
            )
        if status in (301, 302, 303, 307, 308):
            raise err.UnauthorizedError(f"resource {pk}: redirected to {response.headers.get('location')}: the web session is not valid")
        error = err.HTTP_ERRORS_MAP.get(status, err.APIError)
        raise error(f"resource {pk} ({kind}): the server answered {status}")

    # ── collection sub-endpoint ───────────────────────────────────────────────

    @takes_pk(collection_pk=Collection)
    def where_by_collection(
        self,
        collection_pk: int | Collection,
        query: Dict[str, Any] | None = None,
        filter_fn: Callable[[Resource | dict], bool] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> APIQuery[Resource]:
        """Return a lazy iterator over resources belonging to a collection.

        Fetches pages on demand from
        ``/storage/api/resources/collection/{collection_pk}``.

        Args:
            collection_pk: Primary key of the collection.
            query: Base query parameters.
            filter_fn: Optional client-side predicate applied to each item.
            page_size: Number of items requested per API page. Defaults to 50.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            Lazy ``APIQuery`` iterator yielding ``Resource`` instances.

        Example::

            for res in client.resources.where_by_collection(5, status="Public"):
                print(res.pk, res.name)
        """
        endpoint = f"{self.endpoint.rstrip('/')}/collection/{collection_pk}"

        return self.where(
            query=query,
            filter_fn=filter_fn,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=endpoint,
            **kwargs
        )


    @takes_pk(collection_pk=Collection)
    def get_by_collection(
        self,
        collection_pk: int | Collection,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[Resource]:
        """Fetch one page of resources belonging to a collection.

        Args:
            collection_pk: Primary key of the collection.
            query: Base query parameters.
            page: Page number to request. Defaults to ``1``.
            page_size: Number of items per page. Defaults to 50.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``PaginatedResult[Resource]`` for the requested page.

        Example::

            page = client.resources.get_by_collection(5, page=2, page_size=25)
            print(page.pagination.count, len(page.results))
        """
        endpoint = f"{self.endpoint.rstrip('/')}/collection/{collection_pk}"
        return self.get(
            query=query,
            page=page,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=endpoint,
            **kwargs
        )

    @takes_pk(collection_pk=Collection)
    def get_all_by_collection(
        self,
        collection_pk: int | Collection,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[Resource]:
        """Fetch all pages of resources belonging to a collection.

        Args:
            collection_pk: Primary key of the collection.
            query: Base query parameters.
            page_size: Number of items per page requested from the API.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``PaginatedResult[Resource]`` with all items merged from every page.

        Example::

            page = client.resources.get_all_by_collection(5)
            print(page.pagination.count, len(page.results))
        """
        endpoint = f"{self.endpoint.rstrip('/')}/collection/{collection_pk}"
        return self.get_all(
            query=query,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=endpoint,
            **kwargs
        )

    @takes_pk(collection_pk=Collection, resource_pk=(Resource, ClassifiedResource,))
    def find_by_collection(
        self,
        collection_pk: int | Collection,
        resource_pk: int | Resource | ClassifiedResource,
        validate: bool = True,
    ) -> Resource:
        """Retrieve a single resource by PK within a specific collection.

        Args:
            collection_pk: Primary key of the collection.
            resource_pk: Primary key of the resource.
            validate: Whether to return a validated ``Resource`` model.
                If ``False``, the raw response dict is returned instead.

        Returns:
            A ``Resource`` instance when ``validate=True``,
            otherwise the raw response dict.

        Example::

            res = client.resources.find_by_collection(collection_pk=5, resource_pk=123)
            print(res.pk, res.name)
        """
        endpoint = f"{self.endpoint.rstrip('/')}/collection/{collection_pk}/"

        return self.find(
            pk=resource_pk,
            validate=validate,
            overwrite_endpoint=endpoint,
        )

    # ── location sub-endpoint ─────────────────────────────────────────────────

    @takes_pk(location_pk=Location)
    def where_by_location(
        self,
        location_pk: int | Location,
        query: Dict[str, Any] | None = None,
        filter_fn: Callable[[Resource | dict], bool] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> APIQuery[Resource]:
        """Return a lazy iterator over resources at a specific location.

        Fetches pages on demand from
        ``/storage/api/resources/location/{location_pk}``.

        Args:
            location_pk: Primary key of the location.
            query: Base query parameters.
            filter_fn: Optional client-side predicate applied to each item.
            page_size: Number of items requested per API page. Defaults to 50.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            Lazy ``APIQuery`` iterator yielding ``Resource`` instances.

        Example::

            for res in client.resources.where_by_location(42):
                print(res.pk, res.name)
        """
        endpoint = f"{self.endpoint.rstrip('/')}/location/{location_pk}"
        return self.where(
            query=query,
            filter_fn=filter_fn,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=endpoint,
            **kwargs
        )

    @takes_pk(location_pk=Location)
    def get_by_location(
        self,
        location_pk: int | Location,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[Resource]:
        """Fetch one page of resources at a specific location.

        Args:
            location_pk: Primary key of the location.
            query: Base query parameters.
            page: Page number to request. Defaults to ``1``.
            page_size: Number of items per page. Defaults to 50.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``PaginatedResult[Resource]`` for the requested page.

        Example::

            page = client.resources.get_by_location(42, page_size=10)
            print(len(page.results))
        """

        endpoint = f"{self.endpoint.rstrip('/')}/location/{location_pk}"

        return self.get(
            query=query,
            page=page,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=endpoint,
            **kwargs
        )

    @takes_pk(location_pk=Location)
    def get_all_by_location(
        self,
        location_pk: int | Location,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[Resource]:
        """Fetch all pages of resources at a specific location.

        Args:
            location_pk: Primary key of the location.
            query: Base query parameters.
            page_size: Number of items per page requested from the API.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``PaginatedResult[Resource]`` with all items merged from every page.

        Example::

            page = client.resources.get_all_by_location(42)
            print(page.pagination.count)
        """

        endpoint = f"{self.endpoint.rstrip('/')}/location/{location_pk}"
        return self.get_all(
            query=query,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=endpoint,
            **kwargs
        )

    @takes_pk(location_pk=Location, resource_pk=(Resource, ClassifiedResource,))
    def find_by_location(
        self,
        location_pk: int | Location,
        resource_pk: int | Resource | ClassifiedResource,
        validate: bool = True,
    ) -> Resource:
        """Retrieve a single resource by PK at a specific location.

        Args:
            location_pk: Primary key of the location.
            resource_pk: Primary key of the resource.
            validate: Whether to return a validated ``Resource`` model.
                If ``False``, the raw response dict is returned instead.

        Returns:
            A ``Resource`` instance when ``validate=True``,
            otherwise the raw response dict.

        Example::

            res = client.resources.find_by_location(location_pk=42, resource_pk=99)
            print(res.pk, res.name)
        """
        endpoint = f"{self.endpoint.rstrip('/')}/location/{location_pk}"

        return self.find(
            pk=resource_pk,
            validate=validate,
            overwrite_endpoint=endpoint,
        )

    def download_many(
        self,
        resources: Iterable[Resource],
        directory: str | Path,
        kind: Literal["original", "preview", "thumbnail"] = "original",
        skip_existing: bool = True,
        on_error: Literal["continue", "raise"] = "continue",
        progress_callback: Callable[[str, Dict[str, Any]], None] | None = None,
        total: int | None = None,
        retry_attempts: int = 3,
        retry_min_wait: float = 1.0,
        retry_max_wait: float = 10.0,
    ) -> DownloadReport:
        """Download the files of some resources into one folder.

        Each one is saved as ``<name><extension>`` (the extension comes from the resource's ``mime``), with ``-<pk>`` added
        when two resources share a name. A preview or a thumbnail, which Trapper makes as JPEG, is
        ``<name>-preview.jpg`` or ``<name>-thumbnail.jpg``, so that they can share a folder with the originals.
        Trapper has no endpoint for this: it is :meth:`download` once per resource (so the same requirements apply:
        ``user_name``/``user_password``), with a report, and it carries on after a failure by default.

        Args:
            resources: The resources to download (a list, or the lazy ``where()`` iterator).
            directory: The folder; it is created.
            kind: ``"original"``, ``"preview"`` or ``"thumbnail"``.
            skip_existing: Leave alone a file that is already there, so that a run can be repeated after an
                interruption. A file that was cut never exists under its final name (it is a ``.part`` first).
            on_error: ``"continue"`` (default) records the failure in the report and goes on; ``"raise"`` stops at the
                first one.
            progress_callback: ``callback(event, data)``, called with ``"downloaded"``, ``"skipped"`` or ``"failed"`` and
                ``{"resource": ..., "path": ..., "index": n, "total": ...}`` (``"error"`` too, for a failure).
            total: How many resources there are, if known, for the callback.
            retry_attempts: Attempts for each file, the first one included (see :meth:`download`).
            retry_min_wait: Minimum backoff in seconds.
            retry_max_wait: Maximum backoff in seconds.

        Returns:
            A :class:`DownloadReport`.

        Raises:
            ValueError: ``kind`` or ``on_error`` is not valid, or ``user_name``/``user_password`` are missing.
        """
        if kind not in self.media_fields:
            raise ValueError(f"kind must be one of {', '.join(self.media_fields)}, not {kind!r}")
        if on_error not in ("continue", "raise"):
            raise ValueError("on_error must be 'continue' or 'raise'")
        self.client.session_login()

        folder = Path(directory)
        folder.mkdir(parents=True, exist_ok=True)
        report = DownloadReport(directory=folder)
        used: set[str] = set()

        def notify(event: str, resource: Resource, index: int, **extra: Any) -> None:
            if progress_callback:
                progress_callback(event, {"resource": resource, "index": index, "total": total, **extra})

        for index, resource in enumerate(resources, start=1):
            target = folder / self._file_name(resource, kind, used)
            try:
                if skip_existing and target.exists():
                    report.skipped.append(target)
                    notify("skipped", resource, index, path=target)
                    continue
                self.download(resource.pk, target, kind=kind, retry_attempts=retry_attempts,
                              retry_min_wait=retry_min_wait, retry_max_wait=retry_max_wait)
            except Exception as exc:
                if on_error == "raise":
                    raise
                report.failed[resource.pk] = str(exc)
                notify("failed", resource, index, path=target, error=exc)
                continue
            report.downloaded.append(target)
            notify("downloaded", resource, index, path=target)
        return report

    @staticmethod
    def _file_name(resource: Resource, kind: str, used: set[str]) -> str:
        """``<name><extension>`` for a resource, unique among ``used`` (it is added to it)."""
        if kind == "original":
            extension = mimetypes.guess_extension((resource.mime or "").split(";")[0].strip()) or ""
            extension = ".jpg" if extension == ".jpe" else extension
        else:
            extension = ".jpg"
        name = safe_filename(resource.name, fallback=f"resource-{resource.pk}")
        if kind != "original":
            name = f"{name}-{kind}"          # next to the original, not over it
        if extension and name.lower().endswith(extension.lower()):
            name, extension = name[: -len(extension)], name[-len(extension):]       # keep its own spelling
        candidate = f"{name}{extension}"
        if candidate.lower() in used:
            candidate = f"{name}-{resource.pk}{extension}"
        used.add(candidate.lower())
        return candidate
