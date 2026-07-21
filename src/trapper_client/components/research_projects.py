"""
Component for the /research/api/projects resource.
"""

from typing import Any, Dict

from trapper_client.api_query import APIQuery
from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import PaginatedResult, ResearchProject, ResearchProjectCollection
from trapper_client.components.research_project_collections  import (
    ResearchProjectsCollectionsComponent,
)

class ResearchProjectsComponent(TrapperComponent[ResearchProject]):
    """
    Component for the ``/research/api/projects`` resource.

    Available endpoints:
    - ``GET /research/api/projects``: paginated list of accessible research projects
    - ``GET /research/api/projects/{pk}``: single research project

    Related endpoints in the same API module:
    - ``GET /research/api/project/{project_pk}/collections``: collections linked to a project
    - ``GET /research/api/project/{project_pk}/collections/{pk}``: single project-collection link

    Filters for ``/research/api/projects``:
    - ``owner`` (bool): only projects owned/managed by current user
    - ``keywords`` (repeated int): filter by keyword IDs
    - ``acronym`` (str): exact acronym filter
    - ``search`` (str): text search in name, acronym, abstract, owner username
    - ``no-pagination`` (any value): disables pagination in backend

    Example::

        # List all accessible projects
        page = client.research_projects.get(page=1, page_size=50)
        print(page.pagination, len(page.results))

        # Filter by owner and acronym
        for proj in client.research_projects.where(owner=True, acronym="WINTEL"):
            print(proj)

        # Search by text
        for proj in client.research_projects.where(search="Donana"):
            print(proj)

        # Project collections (one page)
        cols = client.research_projects.get_project_collections(project_pk=7)
        print(cols.pagination, len(cols.results))

        # Project collections (lazy iterator)
        for col in client.research_projects.where_project_collections(project_pk=7):
            print(col)

        # Single linked collection
        col = client.research_projects.find_project_collection(project_pk=7, pk=12)
        print(col)

        # Export to CSV
        client.research_projects.export(file="/tmp/research_projects.csv")
    """

    endpoint = "research/api/projects"
    schema = ResearchProject

    def __init__(self, client):
        super().__init__(client)
        self.collections = ResearchProjectsCollectionsComponent(client)

    def get_project_collections(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[ResearchProjectCollection]:
        """Fetch one page of collections linked to a research project.

        Args:
            project_pk: Research project primary key.
            query: Base query parameters.
            page: Page number to fetch.
            page_size: Number of items per page.
            validate: Whether to validate each row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Paginated result containing ``ResearchProjectCollection`` items.
        """
        return self.collections.get_project(project_pk=project_pk, query=query, page=page, page_size=page_size,
                                            validate=validate, **kwargs)

    def where_project_collections(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        **kwargs: Any,
    ) -> APIQuery:
        """Return a lazy iterator over collections linked to a project.

        Args:
            project_pk: Research project primary key.
            query: Base query parameters.
            page_size: Number of items requested per API page.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Lazy ``APIQuery`` iterator yielding project collections.
        """
        return self.collections.where_project(project_pk=project_pk, query=query, page_size=page_size,**kwargs)

    def find_project_collection(
        self,
        project_pk: int,
        pk: int | str,
        query: Dict[str, Any] | None = None,
        validate: bool = True,
        **kwargs: Any,
    ) -> ResearchProjectCollection | Dict[str, Any]:
        """Retrieve one project-collection link by primary key.

        Args:
            project_pk: Research project primary key.
            pk: Project-collection link primary key. NOT collection pk
            query: Base query parameters.
            validate: Whether to validate each row with Pydantic.

        Returns:
            ``ResearchProjectCollection`` when ``validate=True``.
            Otherwise, raw dict-like payload.
        """
        return self.collections.find_project(project_pk=project_pk, pk=pk, query=query, validate=validate,**kwargs)

    def get_all_project_collections(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[ResearchProjectCollection]:
        """Fetch all pages of collections linked to a research project.

        Args:
            project_pk: Research project primary key.
            query: Base query parameters.
            page_size: Number of items requested per API page.
            validate: Whether to validate each row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Paginated result containing merged ``ResearchProjectCollection`` items.
        """
        return self.collections.get_all_project(project_pk=project_pk, query=query, page_size=page_size,
                                                validate=validate,**kwargs)

    def find_collection_in_project(
            self,
            project_pk: int,
            collection_pk: int,
            **kwargs: Any,
    ) -> int | None:
        """Check whether a collection is linked to a research project.

        Iterates the project-collection links lazily and returns the pk of the
        link record if found, or ``None`` if the collection is not linked to
        the project.

        Args:
            project_pk: Research project primary key.
            collection_pk: Collection primary key to search for.
            **kwargs: Extra query parameters passed to the underlying request.

        Returns:
            The pk of the project-collection link if found, otherwise ``None``.

        Example::

            link_pk = client.research_projects.find_collection_in_project(
                project_pk=7,
                collection_pk=42,
            )
            if link_pk:
                print(f"Collection 42 is linked via pk={link_pk}")
            else:
                print("Collection 42 is not in this project")
        """
        return self.collections.find_collection_in_project(
            project_pk=project_pk,
            collection_pk=collection_pk,
            **kwargs,
        )