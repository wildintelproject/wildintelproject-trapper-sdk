"""
Component for the /research/api/project/{project_pk}/collections resource.
"""

from typing import Dict, Any, Callable

from trapper_client.api_query import APIQuery
from trapper_client.components.base import TrapperComponent, versioned
from trapper_client.schemas import PaginatedResult, ResearchProjectCollection


_RP_COLLECTION_FILTERS = frozenset({"owner", "owners", "status", "search", "pk"})


class ResearchProjectsCollectionsComponent(TrapperComponent[ResearchProjectCollection]):
    """
    The collections linked to a research project (``client.research_projects.collections``).

    - ``GET /research/api/project/{project_pk}/collections`` (and ``/{pk}``): one row per link, paginated. A row's
      ``pk`` is the **link's** PK; ``collection_pk`` is the collection's. ``name``, ``owner``, ``status``,
      ``date_created`` and ``description`` are the collection's.

    The list is **empty, not a 403**, unless the research project is approved and the user is its owner or has a
    role in it (a superuser is not exempt): the owner of a project pending approval sees no collection.

    **Filters** (Trapper ignores any other without an error; the SDK emits an ``UnknownFilterWarning``):

    | Parameter | Type | Description |
    |---|---|---|
    | status | choice | The collection's status: ``Private``, ``OnDemand``, ``Public`` |
    | owner | boolean | true = collections the user owns or manages |
    | owners | list of PKs | Owners of the collections |
    | search | text | Collection name or owner's username |

    **Example::**

        for col in client.research_projects.collections.where_project(project_pk=7, status="Private"):
            print(col.pk, col.collection_pk, col.name)

        link_pk = client.research_projects.collections.find_collection_in_project(7, collection_pk=42)
    """

    endpoint = versioned("research/api/project/{project_pk}/collections",
                         ninja="api/v2/research/projects/{project_pk}/collections/")
    schema = ResearchProjectCollection
    known_filters = {"v1": _RP_COLLECTION_FILTERS, "v2": _RP_COLLECTION_FILTERS}

    def where_project(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        filter_fn: Callable | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> APIQuery[ResearchProjectCollection]:
        """Lazy iterator over collections linked to a research project."""

        entrypoint = self.endpoint.format(project_pk=project_pk)

        return self.where(
            query=query,
            filter_fn=filter_fn,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=entrypoint,
            **kwargs,
        )

    def get_project(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[ResearchProjectCollection]:
        """Fetch one page of collections for a research project."""

        entrypoint = self.endpoint.format(project_pk=project_pk)

        return self.get(
            query=query,
            page=page,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=entrypoint,
            **kwargs,
        )

    def get_all_project(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
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
        **kwargs: Any,
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
        **kwargs: Any,
    ) -> int | None:
        """Check whether a collection is linked to a research project."""

        for link in self.where_project(project_pk=project_pk, **kwargs):
            if link.collection_pk == collection_pk:
                return link.pk
        return None