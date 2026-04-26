"""
trapper_api_client.components — Trapper API resource components.

Each component encapsulates the operations for a specific resource type
and is accessible via an attribute of :class:`~trapper_api_client.trapper_client.TrapperClient`.
"""

from trapper_client.components.base import TrapperComponent
from trapper_client.components.locations import LocationsComponent
from trapper_client.components.locations_geojson import LocationsGeoJsonComponent
from trapper_client.components.deployments import DeploymentsComponent
from trapper_client.components.resources import ResourcesComponent
from trapper_client.components.collections import CollectionsComponent
from trapper_client.components.research_projects import ResearchProjectsComponent
from trapper_client.components.classification_projects import ClassificationProjectsComponent
from trapper_client.components.classification_media import ClassificationMediaComponent
from trapper_client.components.classification_results_agg import ClassificationResultsAggComponent
from trapper_client.components.classification_package import ClassificationPackageComponent
from trapper_client.components.ai_classifications import AIClassificationsComponent
from trapper_client.components.user_classifications import UserClassificationsComponent
from trapper_client.components.classifications_map import ClassificationsMapComponent
from trapper_client.components.classificators import ClassificatorsComponent
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
    MediaRecord,
    ClassificationRecordExport,
    ClassificationAggRecord,
    AIClassificationRecord,
    ResultsDataPackageResponse,
)

__all__ = [
    "TrapperComponent",
    "LocationsComponent",
    "LocationsGeoJsonComponent",
    "DeploymentsComponent",
    "ResourcesComponent",
    "CollectionsComponent",
    "ResearchProjectsComponent",
    "ClassificationProjectsComponent",
    "ClassificationMediaComponent",
    "ClassificationRecordExport",
    "ClassificationResultsAggComponent",
    "ClassificationPackageComponent",
    "AIClassificationsComponent",
    "UserClassificationsComponent",
    "ClassificationsMapComponent",
    "ClassificatorsComponent",
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
    "MediaRecord",
    "ClassificationAggRecord",
    "AIClassificationRecord",
    "ResultsDataPackageResponse",
]