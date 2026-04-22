"""
Component for the /research/api/projects resource.
"""

from typing import Any, Dict

from trapper_client.api_query import APIQuery
from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import PaginatedResult, ResearchProject, ResearchProjectCollection


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

    def get_project_collections(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs,
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
        endpoint = f"research/api/project/{project_pk}/collections"
        q = self._merge_query(query, kwargs)
        q = dict(q or {})
        q.setdefault("page", page)
        q.setdefault("page_size", page_size)

        data = self.client.get(endpoint, query=q)
        rows = data.get("results", [])
        parsed = [
            ResearchProjectCollection.model_validate(r)
            if validate
            else ResearchProjectCollection.model_construct(**r)
            for r in rows
        ]

        return PaginatedResult[ResearchProjectCollection](
            pagination={
                "page": data.get("pagination", {}).get("page", 1),
                "page_size": data.get("pagination", {}).get("page_size", len(parsed)),
                "pages": data.get("pagination", {}).get("pages", 1),
                "count": data.get("pagination", {}).get("count", len(parsed)),
            },
            results=parsed,
        )

    def where_project_collections(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        **kwargs,
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
        endpoint = f"research/api/project/{project_pk}/collections"
        q = self._merge_query(query, kwargs)
        return APIQuery(client=self.client, endpoint=endpoint, query=q or {}, page_size=page_size)

    def find_project_collection(
        self,
        project_pk: int,
        pk: int | str,
        query: Dict[str, Any] | None = None,
        validate: bool = True,
        **kwargs,
    ) -> ResearchProjectCollection | Dict[str, Any]:
        """Retrieve one project-collection link by primary key.

        Args:
            project_pk: Research project primary key.
            pk: Project-collection link primary key.
            query: Base query parameters.
            validate: Whether to validate the payload with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            ``ResearchProjectCollection`` when ``validate=True``.
            Otherwise, raw dict-like payload.
        """
        endpoint = f"research/api/project/{project_pk}/collections/{pk}"
        q = self._merge_query(query, kwargs)
        data = self.client.get(endpoint, query=q)
        if validate:
            return ResearchProjectCollection.model_validate(data)
        if isinstance(data, dict):
            return ResearchProjectCollection.model_construct(**data)
        return data

    def get_all_project_collections(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs,
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
        endpoint = f"research/api/project/{project_pk}/collections"
        q = self._merge_query(query, kwargs)
        q = dict(q or {})
        q.setdefault("page_size", page_size)

        data = self.client.get_all(endpoint, query=q)
        rows = data.get("results", [])
        parsed = [
            ResearchProjectCollection.model_validate(r)
            if validate
            else ResearchProjectCollection.model_construct(**r)
            for r in rows
        ]
        return PaginatedResult[ResearchProjectCollection](
            pagination={
                "page": data.get("pagination", {}).get("page", 1),
                "page_size": data.get("pagination", {}).get("page_size", len(parsed)),
                "pages": data.get("pagination", {}).get("pages", 1),
                "count": data.get("pagination", {}).get("count", len(parsed)),
            },
            results=parsed,
        )
