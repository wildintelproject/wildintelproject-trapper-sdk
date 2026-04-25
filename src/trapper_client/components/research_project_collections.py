"""
Component for the /research/api/project/{project_pk}/collections resource.
"""

from typing import Dict, Any, Callable

from trapper_client.api_query import APIQuery
from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import PaginatedResult, ResearchProjectCollection


class ResearchProjectsCollectionsComponent(TrapperComponent[ResearchProjectCollection]):
    """
    Component for the ``/research/api/project/{project_pk}/collections`` resource.

    Retrieve, filter, and iterate collections linked to research projects.

    **Main endpoints:**

    - ``GET /research/api/project/{project_pk}/collections``
    - ``GET /research/api/project/{project_pk}/collections/{pk}``

    **Example::**

        for col in client.research_projects_collections.where_project(project_pk=7):
            print(col)

        page = client.research_projects_collections.get_project(project_pk=7)
        print(page.pagination, len(page.results))
    """

    endpoint = "research/api/project/{project_pk}/collections"
    schema = ResearchProjectCollection

    def where_project(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        filter_fn: Callable | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs,
    ) -> APIQuery[ResearchProjectCollection]:
        """Lazy iterator over collections linked to a research project."""

        entrypoint = self.endpoint.format(project_pk=project_pk)

        return self.where(
            query=query,
            filter_fn=filter_fn,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=entrypoint,
            kwargs=kwargs,
        )

    def get_project(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs,
    ) -> PaginatedResult[ResearchProjectCollection]:
        """Fetch one page of collections for a research project."""

        entrypoint = self.endpoint.format(project_pk=project_pk)

        return self.get(
            query=query,
            page=page,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=entrypoint,
            kwargs=kwargs,
        )

    def get_all_project(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs,
    ) -> PaginatedResult[ResearchProjectCollection]:
        """Fetch all collections for a research project."""

        entrypoint = self.endpoint.format(project_pk=project_pk)

        return self.get_all(
            query=query,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=entrypoint,
            **kwargs,
        )

    def find_project(
        self,
        project_pk: int,
        pk: int | str,
        query: Dict[str, Any] | None = None,
        validate: bool = True,
        **kwargs,
    ) -> ResearchProjectCollection | dict:
        """Retrieve a single project-collection link by PK."""

        entrypoint = self.endpoint.format(project_pk=project_pk)

        return self.find(
            pk=pk,
            validate=validate,
            query=query,
            overwrite_endpoint=entrypoint,
            **kwargs
        )

    def find_collection_in_project(
        self,
        project_pk: int,
        collection_pk: int,
        **kwargs,
    ) -> int | None:
        """Check whether a collection is linked to a research project."""

        for link in self.where_project(project_pk=project_pk, **kwargs):
            if link.collection_pk == collection_pk:
                return link.pk
        return None