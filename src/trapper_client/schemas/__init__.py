"""
Pydantic schemas used by Trapper components.

These models keep a permissive ``extra='allow'`` config so they can parse
API payloads even when fields vary across Trapper deployments.
"""
from .base import Pagination, PaginatedResult, TrapperSchema, TTrapperSchema
from .locations import (
    Location,
    LocationExport,
    LocationGeoJsonGeometry,
    LocationGeoJsonProperties,
    LocationGeoJsonFeature,
    LocationGeoJsonFeatureCollection,
)
from .deployments import Deployment, DeploymentExport
from .project_deployments import (
    ProjectDeployment,
    ProjectDeploymentDetail,
    ProjectDeploymentProgress,
    ProjectLocation,
)
from .resources import Resource
from .collections import Collection
from .research_projects import (
    ResearchProject,
    ResearchProjectCollection,
    ResearchProjectCreate,
    ResearchProjectMember,
    ResearchProjectRole,
)
from .classifications import (
    BBox,
    ClassificationAgg,
    ClassificationImportData,
    ClassificationImportResponse,
    ClassificationProject,
    ClassificationProjectCollection,
    ClassificationProjectCreate,
    ClassificationProjectMember,
    Classification,
    ClassificationRecordExport,
    ClassificationResource,
    ClassificationResourceClassificationData,
    ClassifiedResource,
    ClassificationResultRecordCamtrapDP,
    ClassificationResultRecordTrapper,
    DynamicAttr,
    DynamicAttrValue,
    Media,
    ResultsDataPackageData,
    ResultsDataPackageResponse,
    TrapperClassificationProjectRole,
)
from .ai_classifications import (
    AIClassification,
    AIClassificationRecordExport,
    AIClassificationRecordExportCamTrap,
    AIClassificationRecordExportTrapper,
    AIObservationAttr,
    ResourceAI,
)
from .user_classifications import (
    ResourceUser,
    UserClassification,
    UserObservationAttr,
)
from .classifications_map import (
    ResourceClassificationMap,
    ClassificationMap,
)
from .classificators import ClassificatorCreate, Classificator
from .species import Species
from .maps import Map
from .sequences import Sequence
from .users import User
from trapper_client._deprecated import deprecated_getattr

__all__ = [
    # base
    "Pagination",
    "PaginatedResult",
    "TrapperSchema",
    "TTrapperSchema",
    # locations
    "Location",
    "LocationExport",
    "LocationGeoJsonGeometry",
    "LocationGeoJsonProperties",
    "LocationGeoJsonFeature",
    "LocationGeoJsonFeatureCollection",
    # deployments
    "Deployment",
    "ProjectDeployment",
    "ProjectDeploymentDetail",
    "ProjectDeploymentProgress",
    "ProjectLocation",
    "DeploymentExport",
    # resources
    "Resource",
    # collections
    "Collection",
    # research projects
    "ResearchProject",
    "ResearchProjectCollection",
    "ResearchProjectCreate",
    "ResearchProjectMember",
    "ResearchProjectRole",
    # classifications
    "BBox",
    "ClassificationAgg",
    "ClassificationImportData",
    "ClassificationImportResponse",
    "ClassificationProject",
    "ClassificationProjectCollection",
    "ClassificationProjectCreate",
    "ClassificationProjectMember",
    "Classification",
    "ClassificationRecordExport",
    "ClassificationResource",
    "ClassificationResourceClassificationData",
    "ClassifiedResource",
    "ClassificationResultRecordCamtrapDP",
    "ClassificationResultRecordTrapper",
    "DynamicAttr",
    "DynamicAttrValue",
    "Media",
    "ResultsDataPackageData",
    "ResultsDataPackageResponse",
    "TrapperClassificationProjectRole",
    # ai classifications
    "AIClassification",
    "AIClassificationRecordExport",
    "AIClassificationRecordExportCamTrap",
    "AIClassificationRecordExportTrapper",
    "AIObservationAttr",
    "ResourceAI",
    # user classifications
    "UserClassification",
    "UserObservationAttr",
    "ResourceUser",
    # classifications map
    "ClassificationMap",
    "ResourceClassificationMap",
    # classificators
    "ClassificatorCreate",
    "Classificator",
    # species
    "Species",
    # maps
    "Map",
    # sequences
    "Sequence",
    # users
    "User",
]


__getattr__ = deprecated_getattr(__name__)
