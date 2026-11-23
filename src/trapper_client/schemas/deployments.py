"""Schemas for deployment-related Trapper endpoints."""
from datetime import datetime

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, field_validator, model_validator

from .base import TrapperSchema


_DATETIME = TypeAdapter(datetime)


def _read_datetime(value: Any) -> Any:
    """Read a date from Trapper as a timezone-aware ``datetime``.

    The JSON list gives ``2024-01-01T00:00:00+01:00`` and the CSV export ``2024-01-01T00:00:00+0100``. An
    empty value is ``None``; one that cannot be read is kept as it came, so that a strange value does not
    break a listing.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return _DATETIME.validate_python(value.strip() if isinstance(value, str) else value)
    except ValidationError:
        return value


class Deployment(TrapperSchema):
    """Schema for ``/geomap/api/deployments`` items."""

    pk: int
    deployment_code: str | None = None
    deployment_id: str | None = None

    location: int | None = None
    location_id: str | None = None

    start_date: datetime | str | None = None
    end_date: datetime | str | None = None

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def _dates_as_datetimes(cls, v):
        return _read_datetime(v)

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

    start_date: datetime | str | None = Field(None, alias="deploymentStart")
    end_date: datetime | str | None = Field(None, alias="deploymentEnd")

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def _dates_as_datetimes(cls, v):
        return _read_datetime(v)

    setup_by: str | None = Field(None, alias="setupBy")
    camera_id: str | None = Field(None, alias="cameraID")
    camera_model: str | None = Field(None, alias="cameraModel")
    camera_interval: int | None = Field(None, alias="cameraDelay")
    camera_height: float | None = Field(None, alias="cameraHeight")
    camera_depth: float | None = Field(None, alias="cameraDepth")
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

    @model_validator(mode="before")
    @classmethod
    def _split_groups_and_tags(cls, data: Any) -> Any:
        """Read ``session``, ``array``, ``tags`` and ``bait_type`` from the two columns that hold them.

        Trapper's export has no column for any of those four. ``deploymentGroups`` holds the first two
        (``session:S | array:A``) and ``deploymentTags`` the tags, joined by `` | ``, with
        ``baitType:<value>`` appended when the deployment has a bait type. A value given by its own name
        wins, so a row that already has ``session`` or ``tags`` is left as it is.
        """
        if not isinstance(data, dict):
            return data
        data = dict(data)
        groups = data.pop("deploymentGroups", None)
        tags = data.pop("deploymentTags", None)
        if isinstance(groups, str):
            for part in groups.split("|"):
                key, sep, value = part.partition(":")
                key, value = key.strip(), value.strip()
                if sep and key in ("session", "array") and value and not data.get(key):
                    data[key] = value
        if isinstance(tags, str) and "tags" not in data:
            plain = []
            for name in (t.strip() for t in tags.split("|")):
                if not name:
                    continue
                if name.startswith("baitType:"):
                    if not data.get("bait_type") and not data.get("baitType"):
                        data["bait_type"] = name[len("baitType:"):].strip()
                else:
                    plain.append(name)
            data["tags"] = plain
        return data

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
        "camera_height", "camera_depth", "camera_tilt", "camera_heading",
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
