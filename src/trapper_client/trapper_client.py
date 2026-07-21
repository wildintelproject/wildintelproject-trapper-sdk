"""
TrapperClient — high-level client for the Trapper API.

Exposes domain components as attributes so operations are grouped
by resource type.

Usage::

    from trapper_api_client.trapper_client import TrapperClient

    client = TrapperClient(access_token="mytoken")

    # Locations
    for loc in client.locations.all():
        print(loc)

    # GeoJSON
    geojson = client.locations_geojson.get(collection_id=2)

    # Deployments filtered by collection
    for dep in client.deployments.by_collection(5):
        print(dep)

    # Resources of a storage collection
    for res in client.resources.where_by_collection(collection_pk=3):
        print(res)

    # Research projects
    for proj in client.research_projects.all():
        print(proj)

    # Classification projects
    for proj in client.classification_projects.all():
        print(proj)

    # Classification media export rows for one project
    media_page = client.classification_media.get_project_media(project_pk=7)
    print(media_page.pagination)

    # Classification observations export rows for one project
    obs_page = client.classification_results.get_project_results(project_pk=7)
    print(obs_page.pagination)

    # Classification aggregated results
    agg_page = client.classification_results_agg.get_project_results_agg(project_pk=7)
    print(agg_page.pagination)

    # Classification package metadata and URL
    package = client.classification_package.get_project_package(project_pk=7)
    print(package)
"""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, Type, Union

import attr
from pydantic import BaseModel

from trapper_client.api_client_base import APIClientBase
from trapper_client.api_query import APIQuery
from trapper_client.components import (
    ClassificationProjectsComponent,
    ClassificationsComponent,
    ClassificationMediaComponent,
    ClassificationRecordExport,
    ClassificationResultsAggComponent,
    ClassificationPackageComponent,
    AIClassificationsComponent,
    UserClassificationsComponent,
    ClassificationsMapComponent,
    ClassificatorsComponent,
    SpeciesComponent,
    MapsComponent,
    SequencesComponent,
    UsersComponent,
    CollectionsComponent,
    DeploymentsComponent,
    LocationsComponent,
    LocationsGeoJsonComponent,
    ResearchProjectsComponent,
    ResourcesComponent,
)

logger = logging.getLogger(__name__)


@attr.s
class TrapperClient(APIClientBase):
    """
    High-level client for the Trapper API.

    All resource operations are available through typed component attributes:

    * :attr:`locations` — :class:`~trapper_api_client.components.LocationsComponent`
    * :attr:`locations_geojson` — :class:`~trapper_api_client.components.LocationsGeoJsonComponent`
    * :attr:`deployments` — :class:`~trapper_api_client.components.DeploymentsComponent`
    * :attr:`resources` — :class:`~trapper_api_client.components.ResourcesComponent`
    * :attr:`collections` — :class:`~trapper_api_client.components.CollectionsComponent`
    * :attr:`research_projects` — :class:`~trapper_api_client.components.ResearchProjectsComponent`
    * :attr:`classification_projects` — :class:`~trapper_api_client.components.ClassificationProjectsComponent`
    * :attr:`classification_media` — :class:`~trapper_api_client.components.ClassificationMediaComponent`
    * :attr:`classification_results` - :class:`~trapper_api_client.components.ClassificationsComponent`
    * :attr:`classification_results_agg` - :class:`~trapper_api_client.components.ClassificationResultsAggComponent`
    * :attr:`classification_package` - :class:`~trapper_api_client.components.ClassificationPackageComponent`
    * :attr:`ai_classifications` - :class:`~trapper_api_client.components.AIClassificationsComponent`
    * :attr:`user_classifications` — :class:`~trapper_api_client.components.UserClassificationsComponent`
    * :attr:`classifications_map` — :class:`~trapper_api_client.components.ClassificationsMapComponent`
    * :attr:`classificators` — :class:`~trapper_api_client.components.ClassificatorsComponent`
    * :attr:`species` — :class:`~trapper_api_client.components.SpeciesComponent`
    * :attr:`maps` — :class:`~trapper_api_client.components.MapsComponent`
    * :attr:`sequences` — :class:`~trapper_api_client.components.SequencesComponent`
    * :attr:`users` — :class:`~trapper_api_client.components.UsersComponent`

    Also inherits all low-level helpers from :class:`~trapper_api_client.api_client_base.APIClientBase`
    (``get``, ``post``, ``patch``, ``put``, ``delete``, ``get_all``, ``export_all``, …) and
    the generic :meth:`where` method that returns a lazy :class:`~trapper_api_client.api_query.APIQuery`.

    Attributes:
        access_token: Authentication token (takes precedence over user/password).
        user_name: Username for basic authentication.
        user_password: Password for basic authentication.
        verify_ssl: Whether to verify SSL certificates.
        base_url: Base URL of the Trapper instance.
        timeout: HTTP request timeout in seconds.

    Example::

        client = TrapperClient(access_token="abc123")

        # Lazy iteration
        for loc in client.locations.all():
            print(loc["location_id"], loc["name"])

        # Filter deployments by collection
        for dep in client.deployments.by_collection(3):
            print(dep)

        # Export all locations to CSV
        path = client.locations.export(file="/tmp/locations.csv")

        # Generic endpoint with where()
        for item in client.where("api/deployments/", query={"colls": 7}):
            print(item)
    """

    name = "trapper_client"

    def __attrs_post_init__(self):
        """Initialize base client state and bind resource components.

        Returns:
            ``None``.
        """
        super().__attrs_post_init__()
        self._init_components()

    def _init_components(self):
        """Instantiate and bind all resource components.

        Returns:
            ``None``.
        """
        self.locations: LocationsComponent = LocationsComponent(self)
        self.locations_geojson: LocationsGeoJsonComponent = LocationsGeoJsonComponent(self)
        self.deployments: DeploymentsComponent = DeploymentsComponent(self)
        self.resources: ResourcesComponent = ResourcesComponent(self)
        self.collections: CollectionsComponent = CollectionsComponent(self)
        self.research_projects: ResearchProjectsComponent = ResearchProjectsComponent(self)
        self.classification_projects: ClassificationProjectsComponent = ClassificationProjectsComponent(self)
        self.classification_media: ClassificationMediaComponent = ClassificationMediaComponent(self)
        self.classification_results: ClassificationsComponent = ClassificationsComponent(self)
        self.classification_results_agg: ClassificationResultsAggComponent = ClassificationResultsAggComponent(self)
        self.classification_package: ClassificationPackageComponent = ClassificationPackageComponent(self)
        self.ai_classifications: AIClassificationsComponent = AIClassificationsComponent(self)
        self.user_classifications: UserClassificationsComponent = UserClassificationsComponent(self)
        self.classifications_map: ClassificationsMapComponent = ClassificationsMapComponent(self)
        self.classificators: ClassificatorsComponent = ClassificatorsComponent(self)
        self.species: SpeciesComponent = SpeciesComponent(self)
        self.maps: MapsComponent = MapsComponent(self)
        self.sequences: SequencesComponent = SequencesComponent(self)
        self.users: UsersComponent = UsersComponent(self)

    # ── Generic helper ────────────────────────────────────────────────────────

    def where(
        self,
        endpoint: str,
        query: Dict[str, Any] | None = None,
        schema: Type[BaseModel] | None = None,
        filter_fn: Callable[[Union[BaseModel, dict]], bool] | None = None,
        page_size: int = 50,
    ) -> APIQuery:
        """
        Return a lazy :class:`~trapper_api_client.api_query.APIQuery` iterator over any endpoint.

        Pages are fetched on demand; items are yielded one by one.

        Args:
            endpoint: API endpoint, for example ``"api/deployments/"``.
                Supports ``{placeholder}`` syntax.
            query: Query-string parameters.
            schema: Optional Pydantic model to parse each page response.
            filter_fn: Optional ``(item) -> bool`` predicate for client-side filtering.
            page_size: Number of items requested per API page.

        Returns:
            Lazy ``APIQuery`` iterator.

        Example::

            for item in client.where("api/deployments/", query={"colls": 7}):
                print(item)
        """
        return APIQuery(
            client=self,
            endpoint=endpoint,
            query=query,
            schema=schema,
            filter_fn=filter_fn,
            page_size=page_size,
        )
