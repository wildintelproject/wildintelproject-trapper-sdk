"""
Component for the /api/storage/collections/ resource.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Callable

from trapper_client.api_query import APIQuery
from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import Collection, PaginatedResult


class CollectionsComponent(TrapperComponent[Collection]):
    """
    Component for the ``api/storage/collections/`` resource.

    Retrieve, filter, and export collection data from Trapper.

    **Main endpoints:**

    - ``GET api/storage/collections/``: Paginated list of accessible collections
    - ``GET api/storage/collections/{id}``: Single collection detail
    - ``GET api/storage/collections/{pk}/resources/``: Resources within a collection (lazy iterator)

    - ``GET api/storage/collections_ondemand``: On-demand collections for current user
    - ``GET api/storage/collections_map``: Collections list without pagination (for map rendering)
    - ``GET api/storage/collections_append``: Collections the user can append resources to
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
        for col in client.collections.all():
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
        for res in client.collections.resources(pk=3):
            print(res)

        # Export resources of a collection to CSV
        client.collections.export_resources(pk=3, file="/tmp/resources.csv")
    """

    endpoint = "api/storage/collections/"
    schema = Collection
    _resources_endpoint_tpl = "api/storage/collections/{pk}/resources/"
    _ondemand_endpoint = "api/storage/collections_ondemand"

    def _resources_endpoint(self, pk: int) -> str:
        return self._resources_endpoint_tpl.replace("{pk}", str(pk))

    # ── resources sub-endpoint ────────────────────────────────────────────────

    def where_resources(
        self,
        pk: int,
        query: Dict[str, Any] | None = None,
        filter_fn: Callable | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs,
    ) -> APIQuery:
        """Return a lazy iterator over resources in a specific collection.

        Fetches pages on demand from
        ``api/storage/collections/{pk}/resources/``.

        Args:
            pk: Storage collection primary key.
            query: Base query parameters.
            filter_fn: Optional client-side predicate applied to each item.
            page_size: Number of items requested per API page. Defaults to 50.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            Lazy ``APIQuery`` iterator yielding resource items.

        Example::

            for res in client.collections.where_resources(pk=3, status="Public"):
                print(res)
        """
        q = dict(query or {})
        q.update(kwargs)
        return APIQuery(
            client=self.client,
            endpoint=self._resources_endpoint(pk),
            query=q,
            filter_fn=filter_fn,
            page_size=page_size,
            validate=validate,
        )

    def get_resources(
        self,
        pk: int,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs,
    ) -> PaginatedResult:
        """Fetch one page of resources belonging to a collection.

        Args:
            pk: Storage collection primary key.
            query: Base query parameters.
            page: Page number to request. Defaults to ``1``.
            page_size: Number of items per page. Defaults to 50.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``PaginatedResult`` for the requested page.

        Example::

            page = client.collections.get_resources(pk=3, page=2, page_size=25)
            print(page.pagination.count, len(page.results))
        """
        q = self._merge_query(query, kwargs) or {}
        q.setdefault("page", page)
        q.setdefault("page_size", page_size)
        data = self.client.get(self._resources_endpoint(pk), query=q)
        return self._to_paginated(data, validate=validate)

    def get_all_resources(
        self,
        pk: int,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs,
    ) -> PaginatedResult:
        """Fetch all pages of resources belonging to a collection.

        Args:
            pk: Storage collection primary key.
            query: Base query parameters.
            page_size: Number of items per page requested from the API.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``PaginatedResult`` with all items merged from every page.

        Example::

            page = client.collections.get_all_resources(pk=3)
            print(page.pagination.count, len(page.results))
        """
        q = dict(self._merge_query(query, kwargs) or {})
        q.setdefault("page_size", page_size)
        data = self.client.get_all(self._resources_endpoint(pk), query=q)
        return self._to_paginated(data, validate=validate)

    def find_resource(
        self,
        collection_pk: int,
        resource_pk: int | str,
        validate: bool = True,
    ):
        """Retrieve a single resource by PK within a specific collection.

        Args:
            collection_pk: Storage collection primary key.
            resource_pk: Primary key of the resource.
            validate: Whether to return a validated model.
                If ``False``, the raw response dict is returned.

        Returns:
            Parsed model when ``validate=True``, otherwise the raw dict.

        Example::

            res = client.collections.find_resource(collection_pk=3, resource_pk=99)
            print(res)
        """
        endpoint = f"{self._resources_endpoint(collection_pk).rstrip('/')}/{resource_pk}"
        data = self.client.get(endpoint, query=None)
        return self._to_model(data, validate=validate)

    # ── legacy alias ──────────────────────────────────────────────────────────

    def resources(
        self,
        pk: int,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
    ) -> APIQuery:
        """Alias for :meth:`where_resources`. Kept for backwards compatibility.

        Args:
            pk: Storage collection primary key.
            query: Base query parameters.
            page_size: Number of items requested per API page.

        Returns:
            Lazy ``APIQuery`` iterator yielding collection resources.
        """
        return self.where_resources(pk=pk, query=query, page_size=page_size)

    def export_resources(
        self,
        pk: int,
        query: Dict[str, Any] | None = None,
        file: str | Path | None = None,
    ) -> Path:
        """Export resources of a collection to CSV.

        Args:
            pk: Storage collection primary key.
            query: Base query parameters.
            file: Output CSV file path. If ``None``, a temp file is created.

        Returns:
            Path to the generated CSV file.
        """
        return self.client.export_all(self._resources_endpoint(pk), query=query, file=file)

    # ── on-demand sub-endpoint ────────────────────────────────────────────────

    _ondemand_endpoint = "api/storage/collections_ondemand"

    def where_ondemand(
        self,
        query: Dict[str, Any] | None = None,
        filter_fn: Callable | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs,
    ) -> APIQuery:
        """Return a lazy iterator over on-demand collections for the current user.

        Fetches pages on demand from ``api/storage/collections_ondemand``.

        Args:
            query: Base query parameters.
            filter_fn: Optional client-side predicate applied to each item.
            page_size: Number of items requested per API page. Defaults to 50.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            Lazy ``APIQuery`` iterator yielding ``Collection`` instances.

        Example::

            for col in client.collections.where_ondemand():
                print(col)
        """
        q = dict(query or {})
        q.update(kwargs)
        return APIQuery(
            client=self.client,
            endpoint=self._ondemand_endpoint,
            query=q,
            filter_fn=filter_fn,
            page_size=page_size,
            schema=self.schema,
            validate=validate,
        )

    def get_ondemand(
        self,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs,
    ) -> PaginatedResult:
        """Fetch one page of on-demand collections for the current user.

        Args:
            query: Base query parameters.
            page: Page number to request. Defaults to ``1``.
            page_size: Number of items per page. Defaults to 50.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``PaginatedResult`` for the requested page.

        Example::

            page = client.collections.get_ondemand(page_size=25)
            print(page.pagination.count, len(page.results))
        """
        q = self._merge_query(query, kwargs) or {}
        q.setdefault("page", page)
        q.setdefault("page_size", page_size)
        data = self.client.get(self._ondemand_endpoint, query=q)
        return self._to_paginated(data, validate=validate)

    def get_all_ondemand(
        self,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs,
    ) -> PaginatedResult:
        """Fetch all pages of on-demand collections for the current user.

        Args:
            query: Base query parameters.
            page_size: Number of items per page requested from the API.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``PaginatedResult`` with all items merged from every page.

        Example::

            page = client.collections.get_all_ondemand()
            print(page.pagination.count, len(page.results))
        """
        q = dict(self._merge_query(query, kwargs) or {})
        q.setdefault("page_size", page_size)
        data = self.client.get_all(self._ondemand_endpoint, query=q)
        return self._to_paginated(data, validate=validate)

    def find_ondemand(
        self,
        pk: int | str,
        validate: bool = True,
    ) -> Collection | dict:
        """Retrieve a single on-demand collection by PK.

        Args:
            pk: Collection primary key.
            validate: Whether to return a validated ``Collection`` model.
                If ``False``, the raw response dict is returned.

        Returns:
            A ``Collection`` instance when ``validate=True``,
            otherwise the raw response dict.

        Example::

            col = client.collections.find_ondemand(42)
            print(col)
        """
        data = self.client.get(f"{self._ondemand_endpoint}/{pk}/", query=None)
        return self._to_model(data, validate=validate)

    _map_endpoint = "api/storage/collections_map"

    def where_map(
            self,
            query: Dict[str, Any] | None = None,
            filter_fn: Callable | None = None,
            page_size: int = 50,
            validate: bool = True,
            **kwargs,
    ) -> APIQuery:
        """Return a lazy iterator over  map collections for the current user.

        Fetches pages on demand from ``api/storage/collections_map``.

        Args:
            query: Base query parameters.
            filter_fn: Optional client-side predicate applied to each item.
            page_size: Number of items requested per API page. Defaults to 50.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            Lazy ``APIQuery`` iterator yielding ``Collection`` instances.

        Example::

            for col in client.collections.where_ondemand():
                print(col)
        """
        return self.where(
            query = query,
            filter_fn=filter_fn,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint = self._map_endpoint,
            kwargs = kwargs
        )


    def get_map(
            self,
            query: Dict[str, Any] | None = None,
            page: int = 1,
            page_size: int = 50,
            validate: bool = True,
            **kwargs,
    ) -> PaginatedResult:
        """Fetch one page of map collections for the current user.

        Args:
            query: Base query parameters.
            page: Page number to request. Defaults to ``1``.
            page_size: Number of items per page. Defaults to 50.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``PaginatedResult`` for the requested page.

        Example::

            page = client.collections.get_ondemand(page_size=25)
            print(page.pagination.count, len(page.results))
        """
        return self.get(
            query = query,
            page=page,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint = self._map_endpoint,
            kwargs = kwargs
        )

    def get_all_map(
            self,
            query: Dict[str, Any] | None = None,
            page_size: int = 50,
            validate: bool = True,
            **kwargs,
    ) -> PaginatedResult:
        """Fetch all pages of map collections for the current user.

        Args:
            query: Base query parameters.
            page_size: Number of items per page requested from the API.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``PaginatedResult`` with all items merged from every page.

        Example::

            page = client.collections.get_all_ondemand()
            print(page.pagination.count, len(page.results))
        """

        return self.get_all(
            query=query,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._map_endpoint,
            kwargs=kwargs
        )

    def find_map(
            self,
            pk: int | str,
            validate: bool = True,
    ) -> Collection | dict:
        """Retrieve a single on-demand collection by PK.

        Args:
            pk: Collection primary key.
            validate: Whether to return a validated ``Collection`` model.
                If ``False``, the raw response dict is returned.

        Returns:
            A ``Collection`` instance when ``validate=True``,
            otherwise the raw response dict.

        Example::

            col = client.collections.find_ondemand(42)
            print(col)
        """
        return self.find(
            pk=pk,
            validate=validate,
            overwrite_endpoint=self._map_endpoint,
        )

    _append_endpoint = "api/storage/collections_append"

    def where_append(
            self,
            query: Dict[str, Any] | None = None,
            filter_fn: Callable | None = None,
            page_size: int = 50,
            validate: bool = True,
            **kwargs,
    ) -> APIQuery:
        """Return a lazy iterator over  append collections for the current user.

        Fetches pages on demand from ``api/storage/collections_append``.

        Args:
            query: Base query parameters.
            filter_fn: Optional client-side predicate applied to each item.
            page_size: Number of items requested per API page. Defaults to 50.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            Lazy ``APIQuery`` iterator yielding ``Collection`` instances.

        Example::

            for col in client.collections.where_ondemand():
                print(col)
        """
        return self.where(
            query=query,
            filter_fn=filter_fn,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._append_endpoint,
            kwargs=kwargs
        )

    def get_append(
            self,
            query: Dict[str, Any] | None = None,
            page: int = 1,
            page_size: int = 50,
            validate: bool = True,
            **kwargs,
    ) -> PaginatedResult:
        """Fetch one page of append collections for the current user.

        Args:
            query: Base query parameters.
            page: Page number to request. Defaults to ``1``.
            page_size: Number of items per page. Defaults to 50.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``PaginatedResult`` for the requested page.

        Example::

            page = client.collections.get_ondemand(page_size=25)
            print(page.pagination.count, len(page.results))
        """
        return self.get(
            query=query,
            page=page,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._append_endpoint,
            kwargs=kwargs
        )

    def get_all_append(
            self,
            query: Dict[str, Any] | None = None,
            page_size: int = 50,
            validate: bool = True,
            **kwargs,
    ) -> PaginatedResult:
        """Fetch all pages of append collections for the current user.

        Args:
            query: Base query parameters.
            page_size: Number of items per page requested from the API.
            validate: Whether to run Pydantic validation on each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``PaginatedResult`` with all items merged from every page.

        Example::

            page = client.collections.get_all_ondemand()
            print(page.pagination.count, len(page.results))
        """

        return self.get_all(
            query=query,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._append_endpoint,
            kwargs=kwargs
        )

    def find_append(
            self,
            pk: int | str,
            validate: bool = True,
    ) -> Collection | dict:
        """Retrieve a single on-demand collection by PK.

        Args:
            pk: Collection primary key.
            validate: Whether to return a validated ``Collection`` model.
                If ``False``, the raw response dict is returned.

        Returns:
            A ``Collection`` instance when ``validate=True``,
            otherwise the raw response dict.

        Example::

            col = client.collections.find_ondemand(42)
            print(col)
        """
        return self.find(
            pk=pk,
            validate=validate,
            overwrite_endpoint=self._append_endpoint,
        )