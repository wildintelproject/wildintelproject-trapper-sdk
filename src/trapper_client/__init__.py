"""
trapper_api_client — Python client for the Trapper API.
"""

from trapper_client.api_client_base import APIClientBase
from trapper_client.api_query import APIQuery
from trapper_client.trapper_client import TrapperClient
from trapper_client.components import (
    TrapperComponent,
    LocationsComponent,
    LocationsGeoJsonComponent,
    DeploymentsComponent,
    ResourcesComponent,
    CollectionsComponent,
    ResearchProjectsComponent,
    ClassificationProjectsComponent,
)
from trapper_client.schemas import (
    Pagination,
    PaginatedResult,
    TrapperSchema,
    Location,
    LocationGeoJsonFeatureCollection,
    Deployment,
    Resource,
    Collection,
    ResearchProject,
    ClassificationProject,
)
from trapper_client import err

__all__ = [
    "APIClientBase",
    "APIQuery",
    "TrapperClient",
    "TrapperComponent",
    "LocationsComponent",
    "LocationsGeoJsonComponent",
    "DeploymentsComponent",
    "ResourcesComponent",
    "CollectionsComponent",
    "ResearchProjectsComponent",
    "ClassificationProjectsComponent",
    "Pagination",
    "PaginatedResult",
    "TrapperSchema",
    "Location",
    "LocationGeoJsonFeatureCollection",
    "Deployment",
    "Resource",
    "Collection",
    "ResearchProject",
    "ClassificationProject",
    "err",
]