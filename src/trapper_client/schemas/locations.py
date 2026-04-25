"""Schemas for location-related Trapper endpoints."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .base import TrapperSchema


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
