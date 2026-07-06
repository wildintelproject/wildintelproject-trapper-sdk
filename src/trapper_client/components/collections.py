"""
Component for the /api/storage/collections/ resource.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Callable

from trapper_client.api_query import APIQuery
from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import Collection, PaginatedResult, Resource


class CollectionsComponent(TrapperComponent[Collection]):
    """
    Component for the ``api/storage/collections/`` resource.

    Retrieve, filter, and export collection data from Trapper.

    **Main endpoints:**

    - ``GET /storage/api/collections/``: Paginated list of accessible collections
    - ``GET /storage/api/collections/{id}``: Single collection detail
    - ``GET /storage/api/e/collections_ondemand``: On-demand collections for current user
    - ``GET /storage/api/collections_map``: Collections list for map rendering
    - ``GET /storage/api//collections_append``: Collections the user can append resources to
    - ``POST api/storage/collection/process/``: Trigger processing of an FTP-uploaded collection

    **Available filter fields:**

    - ``pk`` (comma-separated PKs): Filter by specific collection PKs
    - ``status`` (choice): Filter by collection status
    - ``owner`` (boolean): ``true`` = only collections owned/managed by current user
    - ``owners`` (list of PKs): Filter by one or more owner user PKs
    - ``research_projects`` (list of PKs): Filter by one or more research project PKs
    - ``locations_map`` (comma-separated PKs): Filter via ``resources__deployment__location``
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

        # Lazy iteration over resources within a collection
        for res in client.collections.where_resources(pk=3):
            print(res)

        # Export resources of a collection to CSV
        client.collections.export_resources(pk=3, file="/tmp/resources.csv")
    """

    endpoint = "storage/api/collections"
    schema = Collection
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

        Fetches pages on demand from ``api/storage/collections_ondemand``.

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

        Fetches pages on demand from ``api/storage/collections_map``.

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

        Fetches pages on demand from ``api/storage/collections_append``.

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

    def trigger_collection(
            self,
            payload: Dict[str, Any],
            raise_on_error: bool = True,
    ):
        """
        Trigger collection processing on the server.

        Parameters
        ----------
        collection_id : int
            Collection ID.
        payload : dict
            Payload sent to the server.

            Example
            -------
            payload = {
                "yaml_file": "package_123.yaml",
                "zip_file": "package_123.zip",
                "remove_zip": False
            }

        endpoint : str, optional
            Optional endpoint override.
        raise_on_error : bool, optional
            Whether to raise on API error.

        Returns
        -------
        requests.Response
        """

        endpoint = f"/storage/api/collection/process/"

        return self._client.post(
            endpoint=endpoint,
            body=payload,
            raise_on_error=raise_on_error,
        )