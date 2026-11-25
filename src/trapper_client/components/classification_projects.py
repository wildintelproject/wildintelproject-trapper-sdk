"""
Component for the /api/cs/projects/ (classification projects) resource.
"""
from typing import Dict, Any, Iterable

from trapper_client import APIQuery, err
from trapper_client.components.base import TrapperComponent, versioned
from trapper_client.schemas import (
    ClassificationProject,
    ClassificationProjectCreate,
    PaginatedResult,
    ClassificationProjectCollection,
    ClassifiedResource,
)
from trapper_client._pk import takes_pk
from trapper_client.schemas import ClassificationProject, ClassificationProjectCollection, ClassifiedResource, Collection, Resource  # noqa: F401  (pk parameters)


class ClassificationProjectsComponent(TrapperComponent[ClassificationProject]):
    """
    Component for the ``/media_classification/api/projects`` resource.

    Retrieve, filter, and export classification project data from Trapper.

    **Main endpoints:**

    - ``GET /media_classification/api/projects``: (listado, paginado y filtrable por query params)
    - ``GET /media_classification/api/projects/{id}``: (detalle de un proyecto de clasificación)
    - ``GET /media_classification/api/project/{pk}/collections`: collecions en un proyecto de clasificación
    - ``GET /media_classification/api/collection/{collection_pk}/resources/``: recursos clasificados
      dentro de un project-collection link (``collection_pk`` es el pk devuelto por
      ``get_project_collections``/``find_project_collection``, no el pk de la storage collection)



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

    endpoint = versioned("/media_classification/api/projects", ninja="api/v2/classification-projects/")
    schema = ClassificationProject
    endpoint_collections = versioned("/media_classification/api/project/{project_pk}/collections",
                                     ninja="api/v2/classification-projects/{project_pk}/collections/")

    def _collections_entrypoint(self, pk: int):
        return self.endpoint_collections.format(project_pk=pk)

    @takes_pk(project_pk=ClassificationProject)
    def get_project_collections(
        self,
        project_pk: int | ClassificationProject,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[ClassificationProjectCollection]:
        """Fetch one page of collections linked to a classification project.

        Args:
            project_pk: Classification project primary key.
            query: Base query parameters.
            page: Page number to fetch.
            page_size: Number of items per page.
            validate: Whether to validate each row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Paginated result containing ``ClassificationProjectCollection`` items.
        """

        return self.get(
            query=query,
            page=page,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._collections_entrypoint(project_pk),
            overwrite_schema=ClassificationProjectCollection,
            **kwargs,
        )

    @takes_pk(project_pk=ClassificationProject)
    def where_project_collections(
        self,
        project_pk: int | ClassificationProject,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> APIQuery[ClassificationProjectCollection]:
        """Return a lazy iterator over collections linked to a project.

        Args:
            project_pk: Classification project primary key.
            query: Base query parameters.
            page_size: Number of items requested per API page.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Lazy ``APIQuery`` iterator yielding project collections.
        """
        return self.where(
            query=query,
            page_size=page_size,
            overwrite_endpoint=self._collections_entrypoint(project_pk),
            overwrite_schema=ClassificationProjectCollection,
            validate=validate,
            **kwargs,
        )

    @takes_pk(project_pk=ClassificationProject, pk=ClassificationProjectCollection)
    def find_project_collection(
        self,
        project_pk: int | ClassificationProject,
        pk: int | ClassificationProjectCollection,
        query: Dict[str, Any] | None = None,
        validate: bool = True,
        **kwargs: Any,
    ) -> ClassificationProjectCollection:
        """Retrieve one project-collection link by primary key.

        Args:
            project_pk: Classification project primary key.
            pk: Project-collection link primary key. NOT collection pk
        Returns:
            ``ClassificationProjectCollection``
        """
        return self.find(
            pk=pk,
            overwrite_endpoint=self._collections_entrypoint(project_pk),
            overwrite_schema=ClassificationProjectCollection,
            validate=validate,
            query=query,
            **kwargs,
        )

    @takes_pk(project_pk=ClassificationProject)
    def get_all_project_collections(
        self,
        project_pk: int | ClassificationProject,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[ClassificationProjectCollection]:
        """Fetch all pages of collections linked to a classification project.

        Args:
            project_pk: Classification project primary key.
            query: Base query parameters.
            page_size: Number of items requested per API page.
            validate: Whether to validate each row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Paginated result containing merged ``ClassificationProjectCollection`` items.
        """
        return self.get_all(
            query=query,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._collections_entrypoint(project_pk),
            overwrite_schema=ClassificationProjectCollection,
            **kwargs,
        )

    @takes_pk(project_pk=ClassificationProject, collection_pk=Collection)
    def find_collection_in_project(
            self,
            project_pk: int | ClassificationProject,
            collection_pk: int | Collection,
            **kwargs: Any,
    ) -> int | None:
        """Check whether a collection is linked to a classification project.

        Iterates the project-collection links lazily and returns the pk of the
        link record if found, or ``None`` if the collection is not linked to
        the project.

        Args:
            project_pk: Classification project primary key.
            collection_pk: Collection primary key to search for.
            **kwargs: Extra query parameters passed to the underlying request.

        Returns:
            The pk of the project-collection link if found, otherwise ``None``.

        Example::

            link_pk = client.classificacion_projects.find_collection_in_project(
                project_pk=7,
                collection_pk=42,
            )
            if link_pk:
                print(f"Collection 42 is linked via pk={link_pk}")
            else:
                print("Collection 42 is not in this project")
        """
        for link in self.where_project_collections(project_pk=project_pk, **kwargs):
            if link.collection_pk == collection_pk:
                return link.pk
        return None

    # ── write access (Trapper v1: the classic web forms) ──────────────────────

    create_endpoint = "media_classification/project/create/"
    add_collections_endpoint = "media_classification/project/collection/add/"
    remove_collection_endpoint = "media_classification/project/collection/delete/{link_pk}/"
    _ROLES_PREFIX = "classification_project_roles"

    def create(
        self,
        project: ClassificationProjectCreate,
        *,
        raise_on_error: bool = True,
    ) -> ClassificationProject | None:
        """Create a classification project (**Trapper v1 only**).

        The REST API is read-only for classification projects, so this simulates the classic web
        form ``media_classification/project/create/`` with cookie/session authentication, as
        :meth:`~trapper_client.components.research_projects.ResearchProjectsComponent.create` does.
        The account that logs in becomes the owner and administrator. The project is empty: link
        its collections with :meth:`add_collections`.

        Warning:
            It depends on an unversioned HTML form, and needs ``user_name``/``user_password`` (the
            *email* on servers that log in by email): a token alone cannot authenticate it.

        Args:
            project: A :class:`~trapper_client.schemas.classifications.ClassificationProjectCreate`,
                which validates it before anything is sent. The research project must be one the
                account can edit.
            raise_on_error: Raise ``APIError`` when the server rejects the form (the default);
                with ``False`` return ``None`` instead.

        Returns:
            The created project, or ``None`` when it cannot be read back (or the server rejected
            the form and ``raise_on_error=False``).

        Raises:
            TypeError: ``project`` is not a ``ClassificationProjectCreate``.
            err.UnsupportedVersionError: On Trapper v2.
            err.APIError: The server rejected the form (an unknown research project or classificator,
                no permission, ...) or redirected to its login page.

        Example::

            project = client.classification_projects.create(
                ClassificationProjectCreate(name="Doñana 2026", research_project=3, classificator=2)
            )
        """
        self._require_version("v1", feature="classification_projects.create()")
        if not isinstance(project, ClassificationProjectCreate):
            raise TypeError(
                f"create() takes a ClassificationProjectCreate, not {type(project).__name__}; "
                "build one with ClassificationProjectCreate(...) or "
                "ClassificationProjectCreate.model_validate(data)"
            )

        known = {p.pk for p in self.where(search=project.name, page_size=50) if p.name == project.name}
        data = project.to_form()
        data.update(
            self._owner_role_fields(
                self.create_endpoint, self._ROLES_PREFIX, "classification project", project.role_rows()
            )
        )
        if self._submit_create_form(self.create_endpoint, data, "Classification project", raise_on_error) is None:
            return None
        created = [
            p for p in self.where(search=project.name, page_size=50)
            if p.name == project.name and p.pk not in known
        ]
        return max(created, key=lambda p: p.pk, default=None)

    @takes_pk(project_pk=ClassificationProject)
    def add_collections(
        self,
        project_pk: int | ClassificationProject,
        collection_pks: Iterable[int],
    ) -> list[ClassificationProjectCollection]:
        """Link storage collections to a classification project (**Trapper v1 only**).

        Simulates the web action ``media_classification/project/collection/add/``. Trapper only
        takes collections that are already part of the project's *research project*, and where the
        account administers it; linking a collection to a research project is a web action the SDK
        does not cover. A collection that is already in the project is left as it is.

        Args:
            project_pk: Classification project primary key.
            collection_pks: Primary keys of the *storage collections* (``Collection.pk``), not of
                the research-project or project links.

        Returns:
            The project's links for those collections.

        Raises:
            ValueError: A collection is not in the project's research project.
            err.UnsupportedVersionError: On Trapper v2.
            err.APIError: Trapper refused the action, or it left a collection unlinked.
        """
        self._require_version("v1", feature="classification_projects.add_collections()")
        wanted = list(dict.fromkeys(int(pk) for pk in collection_pks))
        if not wanted:
            raise ValueError("collection_pks is empty")

        def links():
            return {l.collection_pk: l for l in self.where_project_collections(project_pk=project_pk)}

        present = links()
        missing = [pk for pk in wanted if pk not in present]
        if missing:
            project = self.find(project_pk)
            research_pk = self._research_project_pk(project.research_project)
            research_links = {
                l.collection_pk: l.pk
                for l in self.client.research_projects.where_project_collections(project_pk=research_pk)
            }
            unknown = [pk for pk in missing if pk not in research_links]
            if unknown:
                raise ValueError(
                    f"collections {unknown} are not in the research project '{project.research_project}' "
                    f"(pk {research_pk}); a classification project can only use the collections of its "
                    "research project"
                )
            response = self.client.session_post_multipart(
                self.add_collections_endpoint,
                data={
                    "project": project_pk,
                    "rproject": research_pk,
                    "collections_pks": ",".join(str(research_links[pk]) for pk in missing),
                },
            )
            self._check_json_action(response, "Adding collections to the classification project")
            present = links()
            still = [pk for pk in missing if pk not in present]
            if still:
                raise err.APIError(f"Trapper accepted the request but collections {still} are still not linked")
        return [present[pk] for pk in wanted]

    @takes_pk(project_pk=ClassificationProject, collection_pk=Collection)
    def remove_collection(self, project_pk: int | ClassificationProject, collection_pk: int | Collection) -> bool:
        """Unlink a collection from a classification project (**Trapper v1 only**).

        Simulates the web action ``media_classification/project/collection/delete/<pk>/``.

        Warning:
            It is irreversible, and the classifications made on that collection **in this project
            are deleted with the link** (the database cascades). The collection and its resources
            are not touched.

        Args:
            project_pk: Classification project primary key.
            collection_pk: Primary key of the *storage collection* to unlink.

        Returns:
            ``True`` once the collection is no longer linked; ``False`` if it never was.

        Raises:
            err.UnsupportedVersionError: On Trapper v2.
            err.APIError: Trapper did not remove it (typically: no permission to edit the project).
        """
        self._require_version("v1", feature="classification_projects.remove_collection()")
        link_pk = self.find_collection_in_project(project_pk=project_pk, collection_pk=collection_pk)
        if link_pk is None:
            return False
        self.client.session_login()
        url = f"{self.client.base_url.rstrip('/')}/{self.remove_collection_endpoint.format(link_pk=link_pk)}"
        self.client._web_client.get(url)
        if self.find_collection_in_project(project_pk=project_pk, collection_pk=collection_pk) is not None:
            raise err.APIError(
                f"Trapper did not unlink collection {collection_pk} from project {project_pk}: "
                "the account may not be allowed to edit the project"
            )
        return True

    def _research_project_pk(self, name: str) -> int:
        """Primary key of a research project from its name (the project API gives only the name).

        Names are unique in Trapper, so an exact match identifies it.
        """
        matches = [p for p in self.client.research_projects.where(search=name, page_size=50) if p.name == name]
        if len(matches) != 1:
            raise err.APIError(f"Cannot tell which research project '{name}' is ({len(matches)} matches)")
        return matches[0].pk

    @staticmethod
    def _check_json_action(response: Any, label: str) -> None:
        """Raise unless a JSON web action (``{"success": ..., "msg": ...}``) succeeded."""
        try:
            body = response.json()
        except ValueError:
            raise err.APIError(f"{label} failed (status {response.status_code}): the answer is not JSON")
        if not body.get("success"):
            raise err.APIError(f"{label} failed: {body.get('msg') or 'no reason given'}")

    # ── classification resources sub-endpoint ────────────────────────────────

    endpoint_resources = versioned("media_classification/api/collection/{collection_pk}/resources/",
                                   ninja="api/v2/classification-collections/{collection_pk}/resources/")

    def _resources_entrypoint(self, collection_pk: int) -> str:
        return self.endpoint_resources.format(collection_pk=collection_pk)

    @takes_pk(collection_pk=ClassificationProjectCollection)
    def get_collection_resources(
        self,
        collection_pk: int | ClassificationProjectCollection,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[ClassifiedResource]:
        """Fetch one page of classified resources within a project-collection link.

        Args:
            collection_pk: Project-collection link primary key (see
                :meth:`get_project_collections`/:meth:`find_project_collection`).
            query: Base query parameters (accepts ``ClassificationFilter`` fields).
            page: Page number to fetch.
            page_size: Number of items per page.
            validate: Whether to validate each row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            ``PaginatedResult[ClassifiedResource]`` for the requested page.
        """
        return self.get(
            query=query,
            page=page,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._resources_entrypoint(collection_pk),
            overwrite_schema=ClassifiedResource,
            **kwargs,
        )

    @takes_pk(collection_pk=ClassificationProjectCollection)
    def where_collection_resources(
        self,
        collection_pk: int | ClassificationProjectCollection,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> APIQuery[ClassifiedResource]:
        """Return a lazy iterator over classified resources within a project-collection link.

        Args:
            collection_pk: Project-collection link primary key.
            query: Base query parameters (accepts ``ClassificationFilter`` fields).
            page_size: Number of items requested per API page.
            validate: Whether to validate each row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Lazy ``APIQuery[ClassifiedResource]`` iterator.
        """
        return self.where(
            query=query,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._resources_entrypoint(collection_pk),
            overwrite_schema=ClassifiedResource,
            **kwargs,
        )

    @takes_pk(collection_pk=ClassificationProjectCollection)
    def get_all_collection_resources(
        self,
        collection_pk: int | ClassificationProjectCollection,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[ClassifiedResource]:
        """Fetch all pages of classified resources within a project-collection link.

        Args:
            collection_pk: Project-collection link primary key.
            query: Base query parameters (accepts ``ClassificationFilter`` fields).
            page_size: Number of items per page requested from the API.
            validate: Whether to validate each row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            ``PaginatedResult[ClassifiedResource]`` with all items merged.
        """
        return self.get_all(
            query=query,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._resources_entrypoint(collection_pk),
            overwrite_schema=ClassifiedResource,
            **kwargs,
        )

    @takes_pk(collection_pk=ClassificationProjectCollection, resource_pk=(Resource, ClassifiedResource,))
    def get_collection_resources_around(
        self,
        collection_pk: int | ClassificationProjectCollection,
        resource_pk: int | Resource | ClassifiedResource,
        size: int = 5,
        query: Dict[str, Any] | None = None,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[ClassifiedResource]:
        """Fetch resources surrounding one resource within a project-collection link.

        Uses the server's windowed pagination (``current``/``size`` query
        params) instead of page-based pagination: returns up to ``size``
        resources on each side of ``resource_pk`` (ordered by
        ``date_recorded``), which is how the classification UI implements
        "previous/next" navigation. The response's ``pagination`` block
        carries ``total``/``filtered`` counts instead of the usual
        ``page``/``pages``/``count`` fields.

        Args:
            collection_pk: Project-collection link primary key.
            resource_pk: Resource primary key to center the window on.
            size: Number of resources to fetch on each side of ``resource_pk``.
            query: Base query parameters (accepts ``ClassificationFilter`` fields).
            validate: Whether to validate each row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            ``PaginatedResult[ClassifiedResource]`` with
            ``pagination.total`` and ``pagination.filtered`` populated.

        Example::

            page = client.classification_projects.get_collection_resources_around(
                collection_pk=12, resource_pk=4831, size=5,
            )
            print(page.pagination.total, page.pagination.filtered)
        """
        q = self._merge_query(query, kwargs)
        q["current"] = resource_pk
        q["size"] = size
        data = self.client.get(self._resources_entrypoint(collection_pk), query=q)
        return self._to_paginated(data, validate=validate, schema=ClassifiedResource)