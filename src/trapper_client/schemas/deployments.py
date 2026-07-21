"""Schemas for deployment-related Trapper endpoints."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .base import TrapperSchema


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

    pk: int | None = Field(None, alias="_id")
    deployment_id: str | None = Field(None, alias="deploymentID")
    location_id: str | None = Field(None, alias="locationID")
    location_name: str | None = Field(None, alias="locationName")

    latitude: float | None = Field(None, alias="latitude")
    longitude: float | None = Field(None, alias="longitude")
    coordinate_uncertainty: float | None = Field(None, alias="coordinateUncertainty")

    start_date: str | None = Field(None, alias="deploymentStart")
    end_date: str | None = Field(None, alias="deploymentEnd")

    setup_by: str | None = Field(None, alias="setupBy")
    camera_id: str | None = Field(None, alias="cameraID")
    camera_model: str | None = Field(None, alias="cameraModel")
    camera_interval: int | None = Field(None, alias="cameraDelay")
    camera_height: float | None = Field(None, alias="cameraHeight")
    camera_tilt: float | None = Field(None, alias="cameraTilt")
    camera_heading: float | None = Field(None, alias="cameraHeading")
    detection_distance: float | None = Field(None, alias="detectionDistance")

    bait_type: str | None = Field(None, alias="baitType")
    bait_use: bool | None = Field(None, alias="baitUse")

    timestamp_issues: bool | None = Field(None, alias="timestampIssues")
    feature_type: str | None = Field(None, alias="featureType")
    habitat: str | None = Field(None, alias="habitat")
    session: str | None = Field(None, alias="session")
    array: str | None = Field(None, alias="array")
    comments: str | None = Field(None, alias="deploymentComments")
    tags: list[str] = Field(default_factory=list)

    @field_validator("pk", "camera_interval", mode="before")
    @classmethod
    def _parse_int(cls, v):
        if v == "" or v is None:
            return None
        try:
            return int(float(v))
        except (ValueError, TypeError):
            return None

    @field_validator(
        "latitude", "longitude", "coordinate_uncertainty",
        "camera_height", "camera_tilt", "camera_heading",
        "detection_distance", mode="before",
    )
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
