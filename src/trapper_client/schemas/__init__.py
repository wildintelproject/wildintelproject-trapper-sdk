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
from .resources import Resource
from .collections import Collection
from .research_projects import ResearchProject, ResearchProjectCollection, ResearchProjectRole
from .classifications import (
    BBox,
    ClassificationAggRecord,
    ClassificationImportData,
    ClassificationImportResponse,
    ClassificationProject,
    ClassificationProjectCollection,
    ClassificationRecord,
    ClassificationRecordExport,
    ClassificationResource,
    ClassificationResourceClassificationData,
    ClassificationResourceRecord,
    ClassificationResultRecordCamtrapDP,
    ClassificationResultRecordTrapper,
    DynamicAttr,
    DynamicAttrValue,
    MediaRecord,
    ResultsDataPackageData,
    ResultsDataPackageResponse,
    TrapperClassificationProjectRole,
)
from .ai_classifications import (
    AIClassificationRecord,
    AIClassificationRecordExport,
    AIClassificationRecordExportCamTrap,
    AIClassificationRecordExportTrapper,
    AIObservationAttr,
    ResourceAI,
)
from .user_classifications import (
    ResourceUser,
    UserClassificationRecord,
    UserObservationAttr,
)
from .classifications_map import (
    ResourceClassificationMap,
    ClassificationMapRecord,
)
from .classificators import ClassificatorRecord
from .species import SpeciesRecord
from .maps import MapRecord
from .sequences import SequenceRecord
from .users import UserRecord

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
    "DeploymentExport",
    # resources
    "Resource",
    # collections
    "Collection",
    # research projects
    "ResearchProject",
    "ResearchProjectCollection",
    "ResearchProjectRole",
    # classifications
    "BBox",
    "ClassificationAggRecord",
    "ClassificationImportData",
    "ClassificationImportResponse",
    "ClassificationProject",
    "ClassificationProjectCollection",
    "ClassificationRecord",
    "ClassificationRecordExport",
    "ClassificationResource",
    "ClassificationResourceClassificationData",
    "ClassificationResourceRecord",
    "ClassificationResultRecordCamtrapDP",
    "ClassificationResultRecordTrapper",
    "DynamicAttr",
    "DynamicAttrValue",
    "MediaRecord",
    "ResultsDataPackageData",
    "ResultsDataPackageResponse",
    "TrapperClassificationProjectRole",
    # ai classifications
    "AIClassificationRecord",
    "AIClassificationRecordExport",
    "AIClassificationRecordExportCamTrap",
    "AIClassificationRecordExportTrapper",
    "AIObservationAttr",
    "ResourceAI",
    # user classifications
    "UserClassificationRecord",
    "UserObservationAttr",
    "ResourceUser",
    # classifications map
    "ClassificationMapRecord",
    "ResourceClassificationMap",
    # classificators
    "ClassificatorRecord",
    # species
    "SpeciesRecord",
    # maps
    "MapRecord",
    # sequences
    "SequenceRecord",
    # users
    "UserRecord",
]
