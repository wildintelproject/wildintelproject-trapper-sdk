"""
Pydantic schemas used by Trapper components.

These models keep a permissive ``extra='allow'`` config so they can parse
API payloads even when fields vary across Trapper deployments.
"""
import json
from datetime import datetime
from typing import Generic, TypeVar, Any, List, Optional, Dict, Annotated, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, HttpUrl

TTrapperSchema = TypeVar("TTrapperSchema", bound="TrapperSchema")


class Pagination(BaseModel):
    """Pagination metadata returned by Trapper endpoints."""

    page: int = 1
    page_size: int = 0
    pages: int = 1
    count: int = 0


class TrapperSchema(BaseModel):
    """Base schema for Trapper API objects."""

    model_config = ConfigDict(extra="allow")


class PaginatedResult(BaseModel, Generic[TTrapperSchema]):
    """Normalized paginated result with typed ``results`` entries."""

    pagination: Pagination
    results: list[TTrapperSchema]


class Location(TrapperSchema):
    """Schema for ``/geomap/api/locations`` items."""

    pk: int
    name: str | None = None
    date_created: datetime | str | None = None
    description: str | None = None
    location_id: str | None = None
    is_public: bool | None = None
    coordinates: str | None = None

    owner: str | None = None
    owner_profile: str | None = None

    city: str | None = None
    county: str | None = None
    state: str | None = None
    country: str | None = None

    research_project: str | None = None
    timezone: str | None = None

    update_data: str | None = None
    delete_data: str | None = None


# en schemas.py

class LocationExport(BaseModel):
    """Schema for /geomap/api/locations/export/ rows.
    """
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    pk: int = Field(alias="_id")
    location_id: str | None = Field(None, alias="locationID")
    longitude: float | None = None
    latitude: float | None = None
    country: str | None = None
    timezone: str | None = None
    ignore_dst: bool | None = Field(None, alias="ignoreDST")
    habitat: str | None = None
    description: str | None = Field(None, alias="comments")
    research_project_id: int | float | None = Field(None, alias="researchProject")

    @field_validator("research_project_id", mode="before")
    @classmethod
    def parse_research_project(cls, v):
        if v == "" or v is None:
            return None
        try:
            return int(float(v))  # convierte '16.0' → 16
        except (ValueError, TypeError):
            return None


class LocationGeoJsonGeometry(BaseModel):
    """GeoJSON geometry object (Point)."""
    model_config = ConfigDict(extra="allow")

    type: str | None = None
    coordinates: list[float] = Field(default_factory=list)


class LocationGeoJsonProperties(TrapperSchema):
    """Properties of a GeoJSON Location feature."""

    pk: int | None = None
    name: str | None = None
    location_id: str | None = None
    description: str | None = None
    owner: str | None = None
    owner_profile: str | None = None
    city: str | None = None
    county: str | None = None
    state: str | None = None
    country: str | None = None
    timezone: str | None = None
    is_public: bool | None = None
    research_project: str | None = None
    date_created: datetime | str | None = None
    update_data: str | None = None
    delete_data: str | None = None


class LocationGeoJsonFeature(BaseModel):
    """A single GeoJSON Feature representing one location."""
    model_config = ConfigDict(extra="allow")

    type: str | None = None
    geometry: LocationGeoJsonGeometry | None = None
    properties: LocationGeoJsonProperties | None = None


class LocationGeoJsonFeatureCollection(BaseModel):
    """Schema for /geomap/api/locations/geojson/ response.

    Represents a GeoJSON FeatureCollection where each feature is a location.
    """
    model_config = ConfigDict(extra="allow")

    type: str | None = None
    features: list[LocationGeoJsonFeature] = Field(default_factory=list)


class Deployment(TrapperSchema):
    """Schema for ``/geomap/api/deployments`` items."""

    pk: int
    deployment_code: str | None = None
    deployment_id: str | None = None

    location: int | None = None
    location_id: str | None = None

    start_date: datetime | str | None = None
    end_date: datetime | str | None = None

    owner: str | None = None
    owner_profile: str | None = None
    research_project: str | None = None

    tags: list[str] = Field(default_factory=list)

    correct_setup: bool | None = None
    correct_tstamp: bool | None = None

    detail_data: str | None = None
    update_data: str | None = None
    delete_data: str | None = None

class DeploymentExport(BaseModel):
    """Schema for deployment export endpoint rows.

    Maps the export CSV field names (camelCase) to Python-friendly names.
    Fields marked as optional may be absent depending on the Trapper deployment.
    """
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    # ── identifiers ───────────────────────────────────────────────────────────
    pk: int | None = Field(None, alias="_id")
    deployment_id: str | None = Field(None, alias="deploymentID")
    location_id: str | None = Field(None, alias="locationID")
    location_name: str | None = Field(None, alias="locationName")

    # ── coordinates ───────────────────────────────────────────────────────────
    latitude: float | None = Field(None, alias="latitude")
    longitude: float | None = Field(None, alias="longitude")
    coordinate_uncertainty: float | None = Field(None, alias="coordinateUncertainty")

    # ── dates ─────────────────────────────────────────────────────────────────
    start_date: str | None = Field(None, alias="deploymentStart")
    end_date: str | None = Field(None, alias="deploymentEnd")

    # ── camera hardware ───────────────────────────────────────────────────────
    setup_by: str | None = Field(None, alias="setupBy")
    camera_id: str | None = Field(None, alias="cameraID")
    camera_model: str | None = Field(None, alias="cameraModel")
    camera_interval: int | None = Field(None, alias="cameraDelay")
    camera_height: float | None = Field(None, alias="cameraHeight")
    camera_tilt: float | None = Field(None, alias="cameraTilt")
    camera_heading: float | None = Field(None, alias="cameraHeading")
    detection_distance: float | None = Field(None, alias="detectionDistance")

    # ── bait ──────────────────────────────────────────────────────────────────
    bait_type: str | None = Field(None, alias="baitType")
    bait_use: bool | None = Field(None, alias="baitUse")

    # ── classification & metadata ─────────────────────────────────────────────
    timestamp_issues: bool | None = Field(None, alias="timestampIssues")
    feature_type: str | None = Field(None, alias="featureType")
    habitat: str | None = Field(None, alias="habitat")
    session: str | None = Field(None, alias="session")
    array: str | None = Field(None, alias="array")
    comments: str | None = Field(None, alias="deploymentComments")
    tags: list[str] = Field(default_factory=list)

    # ── validators ────────────────────────────────────────────────────────────

    @field_validator("pk", "camera_interval", mode="before")
    @classmethod
    def _parse_int(cls, v):
        if v == "" or v is None:
            return None
        try:
            return int(float(v))
        except (ValueError, TypeError):
            return None

    @field_validator("latitude", "longitude", "coordinate_uncertainty",
                     "camera_height", "camera_tilt", "camera_heading",
                     "detection_distance", mode="before")
    @classmethod
    def _parse_float(cls, v):
        if v == "" or v is None:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    @field_validator("timestamp_issues", "bait_use", mode="before")
    @classmethod
    def _parse_bool(cls, v):
        if v == "" or v is None:
            return None
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("true", "1", "yes")
        return bool(v)

class Resource(TrapperSchema):
    """Schema for ``/storage/api/resources`` items."""

    pk: int
    name: str
    owner: str | None = None
    owner_profile: str | None = None
    resource_type: str | None = None
    date_recorded: str | None = None

    observation_type: list[str] = Field(default_factory=list)
    species: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    url: str | None = None
    url_original: str | None = None
    mime: str | None = None
    preview_url: str | None = None
    thumbnail_url: str | None = None

    update_data: str | None = None
    detail_data: str | None = None
    delete_data: str | None = None

    date_recorded_correct: bool | None = None


class Collection(TrapperSchema):
    """Schema for /api/storage/collections/ items."""
    pk: int
    name: str
    owner: Optional[str] = None
    owner_profile: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    update_data: Optional[str] = None
    detail_data: Optional[str] = None
    delete_data: Optional[str] = None

class CollectionCP(TrapperSchema):
    pk: int
    collection_pk: int
    name: str
    status: str
    is_active: bool
    detail_data: str
    classify_data: str
    approved_count: int
    classified_count: int
    total_count: int

class ResearchProjectRole(TrapperSchema):
    """Role entry inside ``ResearchProject.project_roles``."""

    user: str | None = None
    username: str | None = None
    profile: str | None = None
    roles: list[str] = Field(default_factory=list)


class ResearchProjectCollection(TrapperSchema):
    """Schema for ``/research/api/project/{project_pk}/collections`` items."""

    pk: int
    collection_pk: int | None = None
    name: str | None = None
    owner: str | None = None
    owner_profile: str | None = None
    status: bool | int | str | None = None
    date_created: datetime | str | None = None
    description: str | None = None
    detail_data: str | None = None
    delete_data: str | None = None


class ResearchProject(TrapperSchema):
    """Schema for ``/research/api/projects`` items."""

    pk: int
    name: str | None = None
    owner: str | None = None
    owner_profile: str | None = None
    acronym: str | None = None

    keywords: list[str] = Field(default_factory=list)
    date_created: datetime | str | None = None
    project_roles: list[ResearchProjectRole] = Field(default_factory=list)

    update_data: str | None = None
    detail_data: str | None = None
    delete_data: str | None = None

    status: bool | int | str | None = None


class MediaRecord(TrapperSchema):
    """Schema for ``/media_classification/api/media/{project_pk}`` rows."""

    mediaID: int
    deploymentID: str
    captureMethod: str
    timestamp: datetime
    filePath: HttpUrl
    filePublic: bool
    fileName: str
    fileMediatype: str
    exifData: Optional[str] = None
    favorite: bool
    mediaComments: Optional[str] = None
    # id: str = Field(..., alias="_id")

#
# AI Classifications
#
class ResourceAI(BaseModel):
    pk: int
    name: str
    resource_type: str
    thumbnail_url: str
    url: str
    mime: str
    date_recorded: str
    deployment: int
    deployment_id: str

class DynamicAttr(BaseModel):
    observation_type: str
    species: Optional[str] = None
    count: Optional[str] = None
    classification_confidence: Optional[str] = None


class AIClassificationRecord(BaseModel):
    """Schema for ``/media_classification/api/ai-classifications`` items."""

    pk: int
    owner: str
    owner_profile: str
    classification: int

    resource: ResourceAI
    collection: int

    updated_at: str
    created_at: str
    approved: bool

    static_attrs: Dict[str, Any] = Field(default_factory=dict)
    dynamic_attrs: List[DynamicAttr] = Field(default_factory=list)

    detail_data: str
    delete_data: str
    ai_provider: str


class AIClassificationRecordExportCamTrap(TrapperSchema):
    observationID: Optional[int] = None
    deploymentID: str
    mediaID: int
    eventID: str

    eventStart: datetime
    eventEnd: datetime

    observationLevel: str
    observationType: str
    cameraSetupType: Optional[str] = None

    scientificName: Optional[str] = None
    count: Optional[int] = 1

    lifeStage: Optional[str] = None
    sex: Optional[str] = None
    behavior: Optional[str] = None

    individualID: Optional[str] = None

    # 🎯 Bounding box (normalizada)
    bboxX: Optional[float] = Field(None, ge=0, le=1)
    bboxY:  Optional[float] = Field(None, ge=0, le=1)
    bboxWidth:  Optional[float] = Field(None, gt=0, le=1)
    bboxHeight:  Optional[float] = Field(None, gt=0, le=1)

    classificationMethod: Optional[str] = None
    classifiedBy: Optional[str] = None
    classificationTimestamp: Optional[datetime] = None
    classificationProbability: Optional[float] = Field(None, ge=0, le=1)

    observationTags: Optional[str] = None
    observationComments: Optional[str] = None

    # 🧠 Validaciones extra
    #@field_validator("bboxWidth", "bboxHeight")
    #@classmethod
    #def check_bbox_positive(cls, v):
    #    if v <= 0:
    #        raise ValueError("Bounding box width/height must be > 0")
    #    return v

    @field_validator("scientificName")
    @classmethod
    def clean_scientific_name(cls, v):
        if v == "" or v is None:
            return None
        return v

    @field_validator("observationType")
    @classmethod
    def normalize_observation_type(cls, v):
        return v.lower()

    @field_validator("observationID", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v

    @field_validator(
        "bboxX", "bboxY", "bboxWidth", "bboxHeight", "classificationProbability",
        mode="before"
    )
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v

class BBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class AIClassificationRecordExportTrapper(BaseModel):
    observationID: int
    deploymentID: str
    mediaID: int
    eventID: str

    eventStart: datetime
    eventEnd: datetime

    observationLevel: str
    observationType: str

    cameraSetupType: Optional[str] = None
    scientificName: Optional[str] = None

    count: Optional[int] = None

    lifeStage: Optional[str] = None
    sex: Optional[str] = None
    behavior: Optional[str] = None

    individualID: Optional[str] = None
    individualPositionRadius: Optional[float] = None
    individualPositionAngle: Optional[float] = None
    individualSpeed: Optional[float] = None

    bboxX: Optional[float] = None
    bboxY: Optional[float] = None
    bboxWidth: Optional[float] = None
    bboxHeight: Optional[float] = None

    classificationMethod: Optional[str] = None
    classifiedBy: Optional[str] = None
    classificationTimestamp: Optional[datetime] = None
    classificationProbability: Optional[float] = None

    observationTags: Optional[str] = None
    observationComments: Optional[str] = None

    countNew: Optional[int] = None
    englishName: Optional[str] = None

    bboxes: Optional[List[BBox]] = None

    _id: int

    @field_validator('bboxes', mode='before')
    @classmethod
    def parse_bboxes(cls, v):
        if isinstance(v, str):
            parsed = json.loads(v)
            # Si es lista de listas: [[x, y, w, h], ...]
            if parsed and isinstance(parsed[0], list):
                return [BBox(x=b[0], y=b[1], width=b[2], height=b[3]) for b in parsed]
            # Si es lista de dicts: [{"x": ..., "y": ...}, ...]
            return parsed
        return v


AIClassificationRecordExport = Annotated[
    Union[
        AIClassificationRecordExportCamTrap,
        AIClassificationRecordExportTrapper
    ],
    Field(discriminator="_id")
]

#
# Classification
#

class ClassificationResource(BaseModel):
    pk: int
    name: str
    resource_type: str
    thumbnail_url: str
    url: str
    mime: str
    date_recorded: datetime
    deployment: int
    deployment_id: str

class DynamicAttrValue(BaseModel):
    value: Optional[str] = None

class DynamicAttr(BaseModel):
    observation_type: Optional[DynamicAttrValue] = None
    species: Optional[DynamicAttrValue] = None
    count: Optional[DynamicAttrValue] = None

class ClassificationRecord(TrapperSchema):
        pk: int

        resource: Resource
        collection: int

        updated_at: datetime

        is_setup: bool
        static_attrs: Dict[str, Any] = {}

        dynamic_attrs: List[DynamicAttr]

        status: bool
        status_ai: bool
        classified: bool
        classified_ai: bool

        classification_project: str

        detail_data: str
        delete_data: str
        classify_data: str
        update_data: str

        bboxes: bool

class ClassificationResultRecordCamtrapDP(TrapperSchema):
    """Schema for ``/media_classification/api/classifications/results/{project_pk}`` rows."""
    observationID: int
    deploymentID: str
    mediaID: int
    eventID: str
    eventStart: datetime
    eventEnd: datetime
    observationLevel: str
    observationType: str
    cameraSetupType: Optional[str] = None
    scientificName: Optional[str] = None
    count: Optional[int] = None
    lifeStage: Optional[str] = None
    sex: Optional[str] = None
    behavior: Optional[str] = None
    individualID: Optional[str] = None
    individualPositionRadius: Optional[float] = None
    individualPositionAngle: Optional[float] = None
    individualSpeed: Optional[float] = None
    bboxX: Optional[float] = None
    bboxY: Optional[float] = None
    bboxWidth: Optional[float] = None
    bboxHeight: Optional[float] = None
    classificationMethod: Optional[str] = None
    classifiedBy: Optional[str] = None
    classificationTimestamp: Optional[datetime] = None
    classificationProbability: Optional[float] = None
    observationTags: Optional[str] = None
    observationComments: Optional[str] = None

    @field_validator(
        'lifeStage', 'sex', 'behavior', 'individualID',
        'cameraSetupType', 'scientificName', 'observationTags',
        'observationComments', 'classificationMethod', 'classifiedBy',
        mode='before'
    )
    @classmethod
    def empty_str_to_none(cls, v):
        if isinstance(v, str) and v.strip() == '':
            return None
        return v

    @field_validator(
        'individualPositionRadius', 'individualPositionAngle', 'individualSpeed',
        'bboxX', 'bboxY', 'bboxWidth', 'bboxHeight',
        'classificationProbability', 'count',
        mode='before'
    )
    @classmethod
    def empty_numeric_to_none(cls, v):
        if isinstance(v, str) and v.strip() == '':
            return None
        return v

    model_config = {
        "populate_by_name": True,
        "str_strip_whitespace": True,
    }

class ClassificationResultRecordTrapper(TrapperSchema):
    id: int = Field(alias="_id")
    observationID: int
    deploymentID: str
    mediaID: int
    eventID: str
    eventStart: datetime
    eventEnd: datetime
    observationLevel: str
    observationType: str
    cameraSetupType: Optional[str] = None
    scientificName: Optional[str] = None
    count: Optional[int] = None
    lifeStage: Optional[str] = None
    sex: Optional[str] = None
    behavior: Optional[str] = None
    individualID: Optional[str] = None
    individualPositionRadius: Optional[float] = None
    individualPositionAngle: Optional[float] = None
    individualSpeed: Optional[float] = None
    bboxX: Optional[float] = None
    bboxY: Optional[float] = None
    bboxWidth: Optional[float] = None
    bboxHeight: Optional[float] = None
    classificationMethod: Optional[str] = None
    classifiedBy: Optional[str] = None
    classificationTimestamp: Optional[datetime] = None
    classificationProbability: Optional[float] = None
    observationTags: Optional[str] = None
    observationComments: Optional[str] = None
    countNew: Optional[int] = None
    englishName: Optional[str] = None
    bboxes: Optional[List[BBox]] = None

    @field_validator(
        'lifeStage', 'sex', 'behavior', 'individualID', 'cameraSetupType',
        'scientificName', 'observationTags', 'observationComments',
        'classificationMethod', 'classifiedBy', 'englishName',
        mode='before'
    )
    @classmethod
    def empty_str_to_none(cls, v):
        if isinstance(v, str) and v.strip() == '':
            return None
        return v

    @field_validator(
        'individualPositionRadius', 'individualPositionAngle', 'individualSpeed',
        'bboxX', 'bboxY', 'bboxWidth', 'bboxHeight',
        'classificationProbability', 'count', 'countNew',
        mode='before'
    )
    @classmethod
    def empty_numeric_to_none(cls, v):
        if isinstance(v, str) and v.strip() == '':
            return None
        return v

    @field_validator('bboxes', mode='before')
    @classmethod
    def parse_bboxes(cls, v):
        if v is None or (isinstance(v, str) and v.strip() == ''):
            return None
        if isinstance(v, str):
            parsed = json.loads(v)
            if not parsed:
                return None
            # Lista de listas: [[x, y, w, h], ...]
            if isinstance(parsed[0], list):
                return [BBox(x=b[0], y=b[1], width=b[2], height=b[3]) for b in parsed]
            # Lista de dicts: [{"x": ..., "y": ..., "width": ..., "height": ...}, ...]
            return parsed
        return v

    model_config = {
        "populate_by_name": True,
        "str_strip_whitespace": True,
    }


ClassificationRecordExport = Union[
    ClassificationResultRecordCamtrapDP,
    ClassificationResultRecordTrapper,
]

class ClassificationAggRecord(TrapperSchema):
    """Schema for ``/media_classification/api/classifications/results/agg/{project_pk}`` rows."""

    deploymentID: str | None = None
    count: int | str | None = None
    countNew: int | str | None = None
    latitude: float | str | None = None
    longitude: float | str | None = None

#
# Package
#

class ResultsDataPackageData(TrapperSchema):
    """Payload under ``data`` for package generation endpoint responses."""

    message: str | None = None
    errors: Any | None = None
    package: str | None = None


class ResultsDataPackageResponse(TrapperSchema):
    """Schema for ``/media_classification/api/package/{project_pk}`` responses."""

    data: ResultsDataPackageData | None = None



class TrapperClassificationProjectRole(BaseModel):
    user: str
    profile: str
    roles: List[str]

class ClassificationProject(TrapperSchema):
    """Schema for /api/cs/projects/ items."""

    pk: int
    name: str
    owner: str
    owner_profile: str
    classificator: int
    research_project: str
    status: str
    is_active: bool
    project_roles: List[TrapperClassificationProjectRole]
    classificator_removed: bool
    update_data: str
    detail_data: str
    delete_data: str

class ClassificationProjectCollection(TrapperSchema):
    pk: int
    collection_pk: int
    name: str
    status: str
    is_active: bool
    detail_data: str | None = None
    classify_data: str | None = None
    approved_count: int = 0
    classified_count: int = 0
    total_count: int = 0