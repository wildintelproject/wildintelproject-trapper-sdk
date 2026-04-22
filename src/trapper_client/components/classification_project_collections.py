"""
Component for the /api/cs/projects/ (classification projects) resource.
"""
from typing import Dict, Any, Callable

from trapper_client import APIQuery
from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import ClassificationProject, CollectionCP, PaginatedResult


class ClassificationProjectsCollectionsComponent(TrapperComponent[CollectionCP]):
    """
    Component for the ``/media_classification/api/projects`` resource.

    Retrieve, filter, and export classification project data from Trapper.

    **Main endpoints:**

    - ``GET /media_classification/api/projects``: (listado, paginado y filtrable por query params)
    -  ``GET /media_classification/api/projects/{id}``: (detalle de un proyecto de clasificación)


    **Available filter fields:**

    |------------------|-------------|-------------|
    | Parameter        | Type        | Description |
    |------------------|-------------|-------------|
    | owner	           | boolean	 | true = projects where user is owner, manager, or has ANY role
    | status	       | choice	     | Filter by project status
    | research_project | PK	         | Filter by research project FK
    | search           | str         | Searches across: name, owner__username, research_project__name


    ** Example:: **

        for proj in client.classification_projects.all():
            print(proj)

        # Export to CSV
        client.classification_projects.export(file="/tmp/cs_projects.csv")
    """

    endpoint = "/media_classification/api/project/{project_pk}/collections"
    schema = CollectionCP

    def where_classification_project(self,
            project_pk: int,
            query: Dict[str, Any] | None = None,
            filter_fn: Callable | None = None,
            page_size: int = 50,
            validate: bool = True,
            **kwargs,
    ) -> APIQuery[CollectionCP]:
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

        entrypoint = self.endpoint.format(project_pk=project_pk)

        return self.where(
            query=query,
            filter_fn=filter_fn,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=entrypoint,
            kwargs=kwargs
        )

    def get_classification_project(
            self,
            project_pk: int,
            query: Dict[str, Any] | None = None,
            page: int = 1,
            page_size: int = 50,
            validate: bool = True,
            **kwargs,
    ) -> PaginatedResult[CollectionCP]:
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

        entrypoint = self.endpoint.format(project_pk=project_pk)

        return self.get(
            query=query,
            page=page,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=entrypoint,
            kwargs=kwargs
        )

    def get_all_classification_project(
            self,
            project_pk: int,
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
        entrypoint = self.endpoint.format(project_pk=project_pk)

        return self.get_all(
            query=query,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=entrypoint,
            kwargs=kwargs
        )

    def find_classification_project(
            self,
            project_pk: int,
            pk: int | str,
            validate: bool = True,
    ) -> CollectionCP | dict:
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
