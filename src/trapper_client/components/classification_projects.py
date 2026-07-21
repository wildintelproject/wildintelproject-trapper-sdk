"""
Component for the /api/cs/projects/ (classification projects) resource.
"""
from typing import Dict, Any

from trapper_client import APIQuery
from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import (
    ClassificationProject,
    PaginatedResult,
    ClassificationProjectCollection,
    ClassificationResourceRecord,
)


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

    endpoint = "/media_classification/api/projects"
    schema = ClassificationProject
    endpoint_collections="/media_classification/api/project/{project_pk}/collections"

    def _collections_entrypoint(self, pk: int):
        return self.endpoint_collections.format(project_pk=pk)

    def get_project_collections(
        self,
        project_pk: int,
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

    def where_project_collections(
        self,
        project_pk: int,
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

    def find_project_collection(
        self,
        project_pk: int,
        pk: int | str,
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

    def get_all_project_collections(
        self,
        project_pk: int,
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

    def find_collection_in_project(
            self,
            project_pk: int,
            collection_pk: int,
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

    # ── classification resources sub-endpoint ────────────────────────────────

    endpoint_resources = "media_classification/api/collection/{collection_pk}/resources/"

    def _resources_entrypoint(self, collection_pk: int) -> str:
        return self.endpoint_resources.format(collection_pk=collection_pk)

    def get_collection_resources(
        self,
        collection_pk: int,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[ClassificationResourceRecord]:
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
            ``PaginatedResult[ClassificationResourceRecord]`` for the requested page.
        """
        return self.get(
            query=query,
            page=page,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._resources_entrypoint(collection_pk),
            overwrite_schema=ClassificationResourceRecord,
            **kwargs,
        )

    def where_collection_resources(
        self,
        collection_pk: int,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> APIQuery[ClassificationResourceRecord]:
        """Return a lazy iterator over classified resources within a project-collection link.

        Args:
            collection_pk: Project-collection link primary key.
            query: Base query parameters (accepts ``ClassificationFilter`` fields).
            page_size: Number of items requested per API page.
            validate: Whether to validate each row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Lazy ``APIQuery[ClassificationResourceRecord]`` iterator.
        """
        return self.where(
            query=query,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._resources_entrypoint(collection_pk),
            overwrite_schema=ClassificationResourceRecord,
            **kwargs,
        )

    def get_all_collection_resources(
        self,
        collection_pk: int,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[ClassificationResourceRecord]:
        """Fetch all pages of classified resources within a project-collection link.

        Args:
            collection_pk: Project-collection link primary key.
            query: Base query parameters (accepts ``ClassificationFilter`` fields).
            page_size: Number of items per page requested from the API.
            validate: Whether to validate each row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            ``PaginatedResult[ClassificationResourceRecord]`` with all items merged.
        """
        return self.get_all(
            query=query,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._resources_entrypoint(collection_pk),
            overwrite_schema=ClassificationResourceRecord,
            **kwargs,
        )

    def get_collection_resources_around(
        self,
        collection_pk: int,
        resource_pk: int,
        size: int = 5,
        query: Dict[str, Any] | None = None,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[ClassificationResourceRecord]:
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
            ``PaginatedResult[ClassificationResourceRecord]`` with
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
        return self._to_paginated(data, validate=validate, schema=ClassificationResourceRecord)