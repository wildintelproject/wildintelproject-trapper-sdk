"""Schemas for location-related Trapper endpoints."""
import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .base import TrapperSchema

_NUMBER = r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?"
_WKT_PREFIX = re.compile(r"^\s*(?:SRID=\d+;)?\s*POINT\s*\(\s*(.*?)\s*\)\s*$", re.IGNORECASE)
_PAIR = re.compile(rf"^\s*({_NUMBER})\s*(?:,|\s)\s*({_NUMBER})\s*$")


def parse_lon_lat(value: object) -> tuple[float, float] | None:
    """Read the coordinates Trapper gives for a location as ``(longitude, latitude)``.

    Trapper returns one string with the longitude first (``"-6.44, 37.05"``), in v1 and v2. The WKT
    forms (``POINT (-6.44 37.05)``, ``SRID=4326;POINT (-6.44 37.05)``) are read too.

    Returns:
        The two numbers, or ``None`` when ``value`` is missing, cannot be read, or is out of range
        (longitude beyond ±180, latitude beyond ±90): a wrong number is worse than none.
    """
    if not isinstance(value, str):
        return None
    text = value
    wkt = _WKT_PREFIX.match(text)
    if wkt:
        text = wkt.group(1)
    pair = _PAIR.match(text)
    if not pair:
        return None
    longitude, latitude = float(pair.group(1)), float(pair.group(2))
    if not (-180.0 <= longitude <= 180.0 and -90.0 <= latitude <= 90.0):
        return None
    return longitude, latitude


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

    @property
    def longitude(self) -> float | None:
        """Longitude in degrees, read from ``coordinates`` (``None`` if it cannot be read)."""
        point = parse_lon_lat(self.coordinates)
        return point[0] if point else None

    @property
    def latitude(self) -> float | None:
        """Latitude in degrees, read from ``coordinates`` (``None`` if it cannot be read)."""
        point = parse_lon_lat(self.coordinates)
        return point[1] if point else None


class LocationExport(BaseModel):
    """Schema for ``/geomap/api/locations/export/`` rows."""

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
            return int(float(v))
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
    """Schema for ``/geomap/api/locations/geojson/`` response.

    Represents a GeoJSON FeatureCollection where each feature is a location.
    """

    model_config = ConfigDict(extra="allow")

    type: str | None = None
    features: list[LocationGeoJsonFeature] = Field(default_factory=list)
