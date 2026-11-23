"""
Component for the ``storage/api/collections`` resource.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Callable, Literal

import httpx

from trapper_client.api_query import APIQuery
from trapper_client.components.base import TrapperComponent
from trapper_client.components.resources import DownloadReport, ResourcesComponent, safe_filename
from trapper_client.enums import CollectionStatus
from trapper_client.schemas import Collection, PaginatedResult, Resource


class CollectionsComponent(TrapperComponent[Collection]):
    """
    Component for the ``storage/api/collections`` resource.

    Retrieve, filter, and export collection data from Trapper.

    **Main endpoints:**

    - ``GET /storage/api/collections``: Paginated list of accessible collections
    - ``GET /storage/api/collections/{id}``: Single collection detail
    - ``GET /storage/api/collections_ondemand``: On-demand collections for current user, paginated
      (**Trapper v1 only**: ``404`` on v2)
    - ``GET /storage/api/collections_map``: Same fields as the list, but one plain list: **not paginated**
      (``page_size`` is ignored)
    - ``GET /storage/api/collections_append``: Collections the user can append resources to, one plain list
      of ``pk`` and ``name`` only (**not paginated**)
    - ``POST /storage/api/collection/process/``: Trigger processing of an FTP-uploaded collection

    The paginated and the plain endpoints are read through the same methods (``where_map()``, ``get_append()``,
    ...): the plain ones are wrapped as a single page.

    **Available filter fields:**

    - ``pk`` (list of PKs): Filter by specific collection PKs
    - ``status`` (choice): ``Private``, ``OnDemand``, ``Public`` or ``Archived``, in any case
      (:class:`~trapper_client.enums.CollectionStatus`); any other value raises ``ValueError``
    - ``owner`` (boolean): ``true`` = only collections owned/managed by current user
    - ``owners`` (list of PKs): Filter by one or more owner user PKs
    - ``research_projects`` (list of PKs): Filter by one or more research project PKs
    - ``locations_map`` (list of PKs): Filter via ``resources__deployment__location`` (v1 only)
    - ``search`` (string): Full-text search across ``name`` and ``owner__username``

    **Examples:**

        # Retrieve all collections (lazy iteration)
        for col in client.collections.where():
            print(col)

        # Filter by owner
        for col in client.collections.where(owner=True):
            print(col)

        # Filter by research project
        for col in client.collections.where(research_projects=3):
            print(col)

        # Single page
        page = client.collections.get(page=1, page_size=25)
        print(page.pagination.count)

        # Single collection by PK
        col = client.collections.find(42)

        # Lazy iteration over resources within a collection (see ResourcesComponent)
        for res in client.resources.where_by_collection(collection_pk=3):
            print(res)

        # Export resources of a collection to CSV
        client.resources.export(file="/tmp/resources.csv", collections=3)
    """

    endpoint = "storage/api/collections"
    schema = Collection

    # What each version applies (checked live on v1 and v2): a parameter that is not here is ignored.
    _COMMON_FILTERS = frozenset({
        "pk", "status", "owner", "owners", "research_projects", "search", "name", "period_begin", "period_end",
        "is_complete_cs_collection", "cs_deployment", "managers", "members",
    })
    known_filters = {
        "v1": _COMMON_FILTERS | {"locations_map"},
        "v2": _COMMON_FILTERS,       # v2 ignores locations_map: it has no maps
    }

    #: Filters Trapper reads from repeated parameters, and from one comma-separated string.
    _REPEATED_FILTERS = frozenset({"owners", "research_projects", "managers", "members"})
    _COMMA_FILTERS = frozenset({"pk", "locations_map"})

    def _normalize_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Send the list filters the way Trapper reads each one, and check ``status``.

        ``pk=[2, 1]`` keeps one pk in Trapper (``"2,1"`` works). ``status`` is compared as it is, in upper and
        lower case, and a value that does not exist is an empty result, not an error: it is resolved to
        :class:`~trapper_client.enums.CollectionStatus` (any case) and refused with a ``ValueError`` if it is
        none of the four.
        """
        query = self._normalize_lists(query, repeated=self._REPEATED_FILTERS, comma=self._COMMA_FILTERS)
        if query.get("status") is not None:
            query["status"] = CollectionStatus.parse(query["status"], "status").value
        return query
    _ondemand_endpoint = "storage/api/collections_ondemand"
    _map_endpoint = "storage/api/collections_map"
    _append_endpoint = "storage/api/collections_append"

    # ── ondemand sub-endpoint ─────────────────────────────────────────────────

    def where_ondemand(
        self,
        query: Dict[str, Any] | None = None,
        filter_fn: Callable | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> APIQuery[Collection]:
        """Return a lazy iterator over on-demand collections for the current user.

        Fetches pages on demand from ``storage/api/collections_ondemand``.

        Args:
            query: Base query parameters.
            filter_fn: Optional client-side predicate applied to each item.
            page_size: Number of items requested per API page. Defaults to 50.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            Lazy ``APIQuery[Collection]`` iterator yielding ``Collection`` instances.

        Example::

            for col in client.collections.where_ondemand():
                print(col)
        """
        self._require_version("v1", feature="collections.where_ondemand (storage/api/collections_ondemand)")
        return self.where(
            query=query,
            filter_fn=filter_fn,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._ondemand_endpoint,
            **kwargs,
        )

    def get_ondemand(
        self,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[Collection]:
        """Fetch one page of on-demand collections for the current user.

        Args:
            query: Base query parameters.
            page: Page number to request. Defaults to ``1``.
            page_size: Number of items per page. Defaults to 50.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``PaginatedResult[Collection]`` for the requested page.

        Example::

            page = client.collections.get_ondemand(page_size=25)
            print(page.pagination.count, len(page.results))
        """
        self._require_version("v1", feature="collections.get_ondemand (storage/api/collections_ondemand)")
        return self.get(
            query=query,
            page=page,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._ondemand_endpoint,
            **kwargs,
        )

    def get_all_ondemand(
        self,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[Collection]:
        """Fetch all pages of on-demand collections for the current user.

        Args:
            query: Base query parameters.
            page_size: Number of items per page requested from the API.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``PaginatedResult[Collection]`` with all items merged from every page.

        Example::

            page = client.collections.get_all_ondemand()
            print(page.pagination.count, len(page.results))
        """
        self._require_version("v1", feature="collections.get_all_ondemand (storage/api/collections_ondemand)")
        return self.get_all(
            query=query,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._ondemand_endpoint,
            **kwargs,
        )

    def find_ondemand(
        self,
        pk: int | str,
        validate: bool = True,
    ) -> Collection:
        """Retrieve a single on-demand collection by PK.

        Args:
            pk: Collection primary key.
            validate: Whether to run full Pydantic validation.
                If ``False``, the model is constructed without validation.

        Returns:
            ``Collection`` instance, validated or constructed depending on ``validate``.

        Example::

            col = client.collections.find_ondemand(42)
            print(col)
        """
        self._require_version("v1", feature="collections.find_ondemand (storage/api/collections_ondemand)")
        return self.find(
            pk=pk,
            validate=validate,
            overwrite_endpoint=self._ondemand_endpoint,
        )

    # ── map sub-endpoint ──────────────────────────────────────────────────────

    def where_map(
        self,
        query: Dict[str, Any] | None = None,
        filter_fn: Callable | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> APIQuery[Collection]:
        """Return a lazy iterator over map collections for the current user.

        Fetches the plain list of ``storage/api/collections_map`` as one page.

        Args:
            query: Base query parameters.
            filter_fn: Optional client-side predicate applied to each item.
            page_size: Number of items requested per API page. Defaults to 50.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            Lazy ``APIQuery[Collection]`` iterator yielding ``Collection`` instances.

        Example::

            for col in client.collections.where_map():
                print(col)
        """
        return self.where(
            query=query,
            filter_fn=filter_fn,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._map_endpoint,
            **kwargs,
        )

    def get_map(
        self,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[Collection]:
        """Fetch one page of map collections for the current user.

        Args:
            query: Base query parameters.
            page: Page number to request. Defaults to ``1``.
            page_size: Number of items per page. Defaults to 50.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``PaginatedResult[Collection]`` for the requested page.

        Example::

            page = client.collections.get_map(page_size=25)
            print(page.pagination.count, len(page.results))
        """
        return self.get(
            query=query,
            page=page,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._map_endpoint,
            **kwargs,
        )

    def get_all_map(
        self,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[Collection]:
        """Fetch all pages of map collections for the current user.

        Args:
            query: Base query parameters.
            page_size: Number of items per page requested from the API.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``PaginatedResult[Collection]`` with all items merged from every page.

        Example::

            page = client.collections.get_all_map()
            print(page.pagination.count, len(page.results))
        """
        return self.get_all(
            query=query,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._map_endpoint,
            **kwargs,
        )

    def find_map(
        self,
        pk: int | str,
        validate: bool = True,
    ) -> Collection:
        """Retrieve a single map collection by PK.

        Args:
            pk: Collection primary key.
            validate: Whether to run full Pydantic validation.
                If ``False``, the model is constructed without validation.

        Returns:
            ``Collection`` instance, validated or constructed depending on ``validate``.

        Example::

            col = client.collections.find_map(42)
            print(col)
        """
        return self.find(
            pk=pk,
            validate=validate,
            overwrite_endpoint=self._map_endpoint,
        )

    # ── append sub-endpoint ───────────────────────────────────────────────────

    def where_append(
        self,
        query: Dict[str, Any] | None = None,
        filter_fn: Callable | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> APIQuery[Collection]:
        """Return a lazy iterator over append collections for the current user.

        Fetches the plain list of ``storage/api/collections_append`` as one page; its items only have ``pk`` and ``name``.

        Args:
            query: Base query parameters.
            filter_fn: Optional client-side predicate applied to each item.
            page_size: Number of items requested per API page. Defaults to 50.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            Lazy ``APIQuery[Collection]`` iterator yielding ``Collection`` instances.

        Example::

            for col in client.collections.where_append():
                print(col)
        """
        return self.where(
            query=query,
            filter_fn=filter_fn,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._append_endpoint,
            **kwargs,
        )

    def get_append(
        self,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[Collection]:
        """Fetch one page of append collections for the current user.

        Args:
            query: Base query parameters.
            page: Page number to request. Defaults to ``1``.
            page_size: Number of items per page. Defaults to 50.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``PaginatedResult[Collection]`` for the requested page.

        Example::

            page = client.collections.get_append(page_size=25)
            print(page.pagination.count, len(page.results))
        """
        return self.get(
            query=query,
            page=page,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._append_endpoint,
            **kwargs,
        )

    def get_all_append(
        self,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[Collection]:
        """Fetch all pages of append collections for the current user.

        Args:
            query: Base query parameters.
            page_size: Number of items per page requested from the API.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``PaginatedResult[Collection]`` with all items merged from every page.

        Example::

            page = client.collections.get_all_append()
            print(page.pagination.count, len(page.results))
        """
        return self.get_all(
            query=query,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._append_endpoint,
            **kwargs,
        )

    def find_append(
        self,
        pk: int | str,
        validate: bool = True,
    ) -> Collection:
        """Retrieve a single append collection by PK.

        Args:
            pk: Collection primary key.
            validate: Whether to run full Pydantic validation.
                If ``False``, the model is constructed without validation.

        Returns:
            ``Collection`` instance, validated or constructed depending on ``validate``.

        Example::

            col = client.collections.find_append(42)
            print(col)
        """
        return self.find(
            pk=pk,
            validate=validate,
            overwrite_endpoint=self._append_endpoint,
        )

    def download_resources(
        self,
        collection_pk: int,
        directory: str | Path,
        kind: Literal["original", "preview", "thumbnail"] = "original",
        filter_fn: Callable[[Any], bool] | None = None,
        skip_existing: bool = True,
        on_error: Literal["continue", "raise"] = "continue",
        progress_callback: Callable[[str, Dict[str, Any]], None] | None = None,
        retry_attempts: int = 3,
        retry_min_wait: float = 1.0,
        retry_max_wait: float = 10.0,
        **filters: Any,
    ) -> DownloadReport:
        """Download the files of the resources of a collection into ``<directory>/<collection name>/``.

        The resources are listed with ``resources.where_by_collection(collection_pk, **filters)`` and each one is saved with
        :meth:`ResourcesComponent.download` (see :meth:`ResourcesComponent.download_many` for the file names, the
        report and the errors). The folder is flat: the resource list does not say which deployment a resource belongs
        to, so for one folder per deployment use ``client.deployments.download_resources()``. A file that is already in
        the folder is skipped, so a run can be repeated, and a failure does not stop the others. Needs ``user_name``
        and ``user_password``.

        Args:
            collection_pk: Collection primary key. (It is not called ``pk`` because ``pk`` is also a filter of the resource
                list, which this method passes on.)
            directory: Where the folder of the collection goes.
            kind: ``"original"``, ``"preview"`` or ``"thumbnail"``.
            filter_fn: ``predicate(resource) -> bool`` applied on the client to choose which resources.
            skip_existing: Leave alone the files that are already there.
            on_error: ``"continue"`` (default) or ``"raise"`` at the first failure.
            progress_callback: ``callback(event, data)`` for each file (see :meth:`ResourcesComponent.download_many`).
            retry_attempts: Attempts per file (see :meth:`ResourcesComponent.download`).
            retry_min_wait: Minimum backoff in seconds.
            retry_max_wait: Maximum backoff in seconds.
            **filters: Any filter of the resource list: ``resource_type``, ``status``, ``rdate_from``/``rdate_to``,
                ``tags``, ``deployments``, ``search``, ... (see ``client.resources``).

        Returns:
            A :class:`~trapper_client.components.resources.DownloadReport`.

        Example::

            report = client.collections.download_resources(5, "downloads/", deployments=[12, 13], resource_type="I")
            print(report.failed)              # {resource pk: message} of what could not be downloaded
        """
        collection = self.find(collection_pk)
        folder = Path(directory) / safe_filename(collection.name, fallback=f"collection-{collection_pk}")
        resources = ResourcesComponent(self.client)
        total = None if filter_fn else resources.get_by_collection(collection_pk, page_size=1, **filters).pagination.count
        return resources.download_many(
            resources.where_by_collection(collection_pk, filter_fn=filter_fn, page_size=100, **filters), folder, kind=kind,
            skip_existing=skip_existing, on_error=on_error, progress_callback=progress_callback, total=total,
            retry_attempts=retry_attempts, retry_min_wait=retry_min_wait, retry_max_wait=retry_max_wait,
        )

    def trigger_collection(
            self,
            payload: Dict[str, Any],
            raise_on_error: bool = True,
    ) -> httpx.Response:
        """Start the processing of a collection that was uploaded to the account's FTP folder.

        ``POST /storage/api/collection/process/``. Trapper checks the YAML definition and starts a task that
        reads the ZIP and creates the collection and its resources; the answer is ``{"data": {"message": ...,
        "errors": ..., "task_id": ...}}``. The task runs in the background (``task_id`` identifies it; only a server
        with Celery off runs it in the request), so a ``200`` means it was started, not that the collection exists.

        Args:
            payload: The JSON body. ``yaml_file`` and ``zip_file`` are required: the names of two files that are
                already in the **account's own external folder** on the server. The rest is optional:
                ``remove_zip`` (default ``False``: delete the ZIP when done), ``extract_metadata`` (default
                ``False``) and ``trigger_ai_pipeline`` (default ``True``).
            raise_on_error: Raise the mapped exception for an error answer (see below). With ``False`` the
                ``httpx.Response`` is returned whatever its status.

        Returns:
            The raw ``httpx.Response``; ``response.json()["data"]["task_id"]`` is the task.

        Raises:
            err.BadRequestError: ``yaml_file`` or ``zip_file`` is missing (``"Both 'yaml_file' and 'zip_file' must
                be provided."``), or the YAML definition is invalid (the problems are in ``data.errors``).
            err.NotFoundError: One of the two files is not in the account's folder on the server.

        Example::

            response = client.collections.trigger_collection({
                "yaml_file": "package_123.yaml",
                "zip_file": "package_123.zip",
                "remove_zip": False,
            })
            print(response.json()["data"]["task_id"])
        """

        endpoint = f"/storage/api/collection/process/"

        return self.client.post(
            endpoint=endpoint,
            body=payload,
            raise_on_error=raise_on_error,
        )
