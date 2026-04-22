"""
Component for the /storage/api/resources/ resource.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import PaginatedResult, Resource
from trapper_client.api_query import APIQuery


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
    | ``locations_map``          | comma-separated PKs         | Filter via ``deployment__location``                          |
    +----------------------------+-----------------------------+--------------------------------------------------------------+
    | ``collections``            | list of PKs                 | Filter by one or more collection PKs                         |
    +----------------------------+-----------------------------+--------------------------------------------------------------+
    | ``deployments``            | repeatable PKs              | Filter by deployment PKs                                     |
    +----------------------------+-----------------------------+--------------------------------------------------------------+
    | ``deployment__isnull``     | boolean                     | ``true`` = resources with no deployment                      |
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

    endpoint = "storage/api/resources"
    schema = Resource

    # ── collection sub-endpoint ───────────────────────────────────────────────

    def where_by_collection(
        self,
        collection_pk: int,
        query: Dict[str, Any] | None = None,
        filter_fn: Callable[[Resource | dict], bool] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs,
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


    def get_by_collection(
        self,
        collection_pk: int,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs,
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

    def get_all_by_collection(
        self,
        collection_pk: int,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs,
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

    def find_by_collection(
        self,
        collection_pk: int,
        resource_pk: int | str,
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

    def where_by_location(
        self,
        location_pk: int,
        query: Dict[str, Any] | None = None,
        filter_fn: Callable[[Resource | dict], bool] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs,
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

    def get_by_location(
        self,
        location_pk: int,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs,
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

    def get_all_by_location(
        self,
        location_pk: int,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs,
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

    def find_by_location(
        self,
        location_pk: int,
        resource_pk: int | str,
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