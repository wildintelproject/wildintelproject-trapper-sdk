"""Schemas for the deployments of a classification project (Trapper v2, ``api/deployments/<slug>/``)."""
from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import TrapperSchema


class ProjectDeploymentOwner(TrapperSchema):
    id: int
    name: str
    avatar: str | None = None


class ProjectDeploymentThumbnail(TrapperSchema):
    pk: int
    thumbnail: str | None = None


class ProjectDeploymentSpecies(TrapperSchema):
    total: int
    latin_name: str | None = None
    english_name: str | None = None


class ProjectDeployment(TrapperSchema):
    """One row of ``GET api/deployments/<slug>/``."""

    pk: int
    deployment_id: str | None = None
    deployment_code: str | None = None
    location_name: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    sequences: int = 0
    owner: ProjectDeploymentOwner | None = None
    thumbnails: list[ProjectDeploymentThumbnail] = Field(default_factory=list)
    species: list[ProjectDeploymentSpecies] = Field(default_factory=list)
    can_update: bool = False
    can_delete: bool = False


class ProjectDeploymentLocation(TrapperSchema):
    """Embedded location of a deployment."""

    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class ProjectDeploymentDetail(ProjectDeployment):
    """``GET`` / ``PATCH api/deployments/<slug>/<pk>/``: the editable deployment."""

    location_id: int | None = None
    location: ProjectDeploymentLocation | None = None
    camera_id: str | None = None
    camera_model: str | None = None
    camera_interval: int | None = None
    camera_height: str | float | None = None
    camera_tilt: int | None = None
    camera_heading: int | None = None
    detection_distance: float | None = None
    bait_type: int | None = None
    feature_type: str | None = None
    habitat: str | None = None
    timestamp_issues: bool = False
    comments: str | None = None
    is_private: bool = True
    is_incomplete: bool = False
    resources_count: int | None = None
    classified_ai_count: int | None = None
    classified_by_me_count: int | None = None
    classified_expert_count: int | None = None
    media: Any = None
    media_state: Any = None


class ProjectLocation(TrapperSchema):
    """One row of ``GET api/deployments/<slug>/locations/``."""

    pk: int
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    deployments_count: int = 0


class ProjectDeploymentProgress(TrapperSchema):
    """``GET api/deployments/<slug>/<pk>/progress/``: AI pipeline progress."""

    pk: int
    deployment_id: str | None = None
    running: bool = False
    stages: list[dict[str, Any]] = Field(default_factory=list)
