"""Schemas for classification-related Trapper endpoints."""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from .base import TrapperSchema
from .resources import Resource


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


class BBox(BaseModel):
    """Bounding box coordinates (normalised 0–1)."""

    x: float
    y: float
    width: float
    height: float


class ClassificationResource(BaseModel):
    """Embedded resource inside a classification record."""

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
    """A single dynamic attribute value cell."""

    value: Optional[str] = None


class DynamicAttr(BaseModel):
    """Dynamic observation attributes attached to a classification record."""

    observation_type: Optional[DynamicAttrValue] = None
    species: Optional[DynamicAttrValue] = None
    count: Optional[DynamicAttrValue] = None


class ClassificationResourceClassificationData(BaseModel):
    """Nested ``classification_data`` block inside a classification-resource row."""

    pk: int
    url: str
    is_approved: bool
    is_classified: bool


class ClassificationResourceRecord(TrapperSchema):
    """Schema for ``/media_classification/api/collection/{collection_pk}/resources/`` items."""

    pk: int
    name: str
    thumbnail_url: str
    url: str
    mime: str
    resource_type: str
    date_recorded: datetime
    sequence: str | None = None
    classification_data: ClassificationResourceClassificationData


class ClassificationImportData(TrapperSchema):
    """Payload under ``data`` for the classification import endpoint response."""

    message: str | None = None
    errors: Any | None = None
    task_id: str | None = None


class ClassificationImportResponse(TrapperSchema):
    """Schema for ``POST /media_classification/api/classifications/import/`` responses."""

    data: ClassificationImportData | None = None


class ClassificationRecord(TrapperSchema):
    """Schema for ``/media_classification/api/classifications`` items."""

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
    """CamtrapDP-flavoured row from ``/media_classification/api/classifications/results/{project_pk}``."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

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
        "lifeStage", "sex", "behavior", "individualID",
        "cameraSetupType", "scientificName", "observationTags",
        "observationComments", "classificationMethod", "classifiedBy",
        mode="before",
    )
    @classmethod
    def empty_str_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator(
        "individualPositionRadius", "individualPositionAngle", "individualSpeed",
        "bboxX", "bboxY", "bboxWidth", "bboxHeight",
        "classificationProbability", "count",
        mode="before",
    )
    @classmethod
    def empty_numeric_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator("classificationTimestamp", mode="before")
    @classmethod
    def empty_datetime_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


class ClassificationResultRecordTrapper(TrapperSchema):
    """Trapper-flavoured row from ``/media_classification/api/classifications/results/{project_pk}``."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

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
        "lifeStage", "sex", "behavior", "individualID", "cameraSetupType",
        "scientificName", "observationTags", "observationComments",
        "classificationMethod", "classifiedBy", "englishName",
        mode="before",
    )
    @classmethod
    def empty_str_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator(
        "individualPositionRadius", "individualPositionAngle", "individualSpeed",
        "bboxX", "bboxY", "bboxWidth", "bboxHeight",
        "classificationProbability", "count", "countNew",
        mode="before",
    )
    @classmethod
    def empty_numeric_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator("classificationTimestamp", mode="before")
    @classmethod
    def empty_datetime_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator("bboxes", mode="before")
    @classmethod
    def parse_bboxes(cls, v):
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        if isinstance(v, str):
            parsed = json.loads(v)
            if not parsed:
                return None
            if isinstance(parsed[0], list):
                return [BBox(x=b[0], y=b[1], width=b[2], height=b[3]) for b in parsed]
            return parsed
        return v


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


class ResultsDataPackageData(TrapperSchema):
    """Payload under ``data`` for package generation endpoint responses."""

    message: str | None = None
    errors: Any | None = None
    package: str | None = None


class ResultsDataPackageResponse(TrapperSchema):
    """Schema for ``/media_classification/api/package/{project_pk}`` responses."""

    data: ResultsDataPackageData | None = None


class TrapperClassificationProjectRole(BaseModel):
    """Role entry inside a classification project."""

    user: str
    profile: str
    roles: List[str]


class ClassificationProject(TrapperSchema):
    """Schema for ``/api/cs/projects/`` items."""

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
    """Schema for collection entries inside a classification project."""

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
