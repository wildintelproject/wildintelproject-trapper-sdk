"""Schemas for AI classification Trapper endpoints."""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .base import TrapperSchema
from .classifications import BBox


class ResourceAI(BaseModel):
    """Resource entry embedded inside an AI classification record."""

    pk: int
    name: str
    resource_type: str
    thumbnail_url: str
    url: str
    mime: str
    date_recorded: str
    deployment: int
    deployment_id: str


class AIObservationAttr(BaseModel):
    """A single observation attribute returned by the AI classifier."""

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
    dynamic_attrs: List[AIObservationAttr] = Field(default_factory=list)

    detail_data: str
    delete_data: str
    ai_provider: str


class AIClassificationRecordExportCamTrap(TrapperSchema):
    """CamtrapDP-flavoured row from the AI classification export endpoint."""

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

    bboxX: Optional[float] = Field(None, ge=0, le=1)
    bboxY: Optional[float] = Field(None, ge=0, le=1)
    bboxWidth: Optional[float] = Field(None, gt=0, le=1)
    bboxHeight: Optional[float] = Field(None, gt=0, le=1)

    classificationMethod: Optional[str] = None
    classifiedBy: Optional[str] = None
    classificationTimestamp: Optional[datetime] = None
    classificationProbability: Optional[float] = Field(None, ge=0, le=1)

    observationTags: Optional[str] = None
    observationComments: Optional[str] = None

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

    @field_validator(
        "observationID",
        "bboxX", "bboxY", "bboxWidth", "bboxHeight", "classificationProbability",
        mode="before",
    )
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v


class AIClassificationRecordExportTrapper(BaseModel):
    """Trapper-flavoured row from the AI classification export endpoint."""

    model_config = ConfigDict(populate_by_name=True)

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

    @field_validator("bboxes", mode="before")
    @classmethod
    def parse_bboxes(cls, v):
        if isinstance(v, str):
            parsed = json.loads(v)
            if parsed and isinstance(parsed[0], list):
                return [BBox(x=b[0], y=b[1], width=b[2], height=b[3]) for b in parsed]
            return parsed
        if isinstance(v, list) and v and isinstance(v[0], list):
            return [BBox(x=b[0], y=b[1], width=b[2], height=b[3]) for b in v]
        return v


AIClassificationRecordExport = Union[
    AIClassificationRecordExportCamTrap,
    AIClassificationRecordExportTrapper,
]
