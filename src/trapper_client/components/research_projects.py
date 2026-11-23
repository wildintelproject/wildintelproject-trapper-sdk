"""
Component for the /research/api/projects resource.
"""

from typing import Any, Dict

from trapper_client import err
from trapper_client.api_query import APIQuery
from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import (
    PaginatedResult,
    ResearchProject,
    ResearchProjectCollection,
    ResearchProjectCreate,
)
from trapper_client.components.research_project_collections  import (
    ResearchProjectsCollectionsComponent,
)

_ROLES_PREFIX = "project_roles"


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

    create_endpoint = "research/project/create/"

    def create(
        self,
        request: ResearchProjectCreate,
        *,
        raise_on_error: bool = True,
    ) -> ResearchProject | None:
        """Create a research project (**Trapper v1 only**).

        Trapper's REST API is read-only for research projects, so this simulates the classic web
        form ``research/project/create/`` with cookie/session authentication, the same workaround
        :meth:`~trapper_client.components.locations.LocationsComponent.import_locations` uses.
        The account that logs in becomes the project's owner and its administrator.

        Warning:
            This depends on an unversioned HTML form, not a documented API contract, and it needs
            ``user_name``/``user_password`` (the account's *email* on servers that log in by
            email): an access token alone cannot authenticate it.

        Args:
            request: The project to create, as a
                :class:`~trapper_client.schemas.research_projects.ResearchProjectCreate`, which
                validates it before anything is sent. ``name`` and ``acronym`` (3 to 10
                characters) must be unique; the sampling design, sensor method, animal types and
                bait use are the enumerations of :mod:`trapper_client.enums`.
            raise_on_error: Raise ``APIError`` when the server rejects the form (the default);
                with ``False`` return ``None`` instead.

        Returns:
            The created project. ``None`` when the project was created but cannot be read back
            yet: Trapper only activates the projects of staff accounts at once, and hides the
            others from the API until an administrator approves them. (Also ``None`` when the
            server rejects the form and ``raise_on_error=False``.)

        Raises:
            TypeError: ``request`` is not a ``ResearchProjectCreate``.
            err.UnsupportedVersionError: On Trapper v2.
            err.APIError: The server rejected the form (a name or acronym already in use, ...) or
                redirected to its login page.

        Example::

            project = client.research_projects.create(
                ResearchProjectCreate(
                    name="Doñana mammals",
                    acronym="DONMAM",
                    sampling_design=SamplingDesign.TARGETED,
                    bait_use=BaitUse.SCENT,
                    keywords=["camera trap", "mammals"],
                )
            )
        """
        self._require_version("v1", feature="research_projects.create()")
        if not isinstance(request, ResearchProjectCreate):
            raise TypeError(
                f"create() takes a ResearchProjectCreate, not {type(request).__name__}; "
                "build one with ResearchProjectCreate(...) or ResearchProjectCreate.model_validate(data)"
            )
        acronym = request.acronym

        data = request.to_form()
        data.update(
            self._owner_role_fields(
                self.create_endpoint, _ROLES_PREFIX, "research project", request.role_rows()
            )
        )

        if self._submit_create_form(self.create_endpoint, data, "Research project", raise_on_error) is not None:
            return next(iter(self.where(acronym=acronym, page_size=5)), None)
        return None

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