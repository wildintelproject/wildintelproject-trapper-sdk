"""
Component for the deployments of a classification project (Trapper v2 only).

Trapper v2 serves ``/api/deployments/<slug>/...``: the deployments a user can see in one
classification project, plus the actions on them (edit, delete, shift timestamps, AI progress and
calibration). ``<slug>`` is the project's ``slug`` and the project must be a Citizen Science one
(``citizen_science_status`` public or private) with a classificator.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable

from trapper_client.api_query import APIQuery
from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import (
    PaginatedResult,
    ProjectDeployment,
    ProjectDeploymentDetail,
    ProjectDeploymentProgress,
    ProjectLocation,
)


class ProjectDeploymentsComponent(TrapperComponent[ProjectDeployment]):
    """
    Deployments of a classification project, and the actions on each of them (Trapper v2).

    Every method takes the project's ``slug`` first. On a v1 server they raise
    :class:`~trapper_client.err.UnsupportedVersionError`.

    **Examples:**

        slug = "mamiferos-donana-sm"

        for dep in client.project_deployments.where(slug):
            print(dep.deployment_id, dep.location_name, [s.latin_name for s in dep.species])

        dep = client.project_deployments.find(slug, 3)
        client.project_deployments.update(slug, 3, comments="Camera moved 2 m north")
        client.project_deployments.update_timestamps(slug, 3, time_offset=3600)   # +1 h
        print(client.project_deployments.progress(slug, 3).running)
    """

    endpoint = "api/deployments"
    schema = ProjectDeployment
    supported_versions = ("v2",)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _url(self, project_slug: str, *parts: Any) -> str:
        tail = "/".join(str(p) for p in parts)
        return f"{self.endpoint}/{project_slug}/{tail}/" if tail else f"{self.endpoint}/{project_slug}/"

    def _single(self, endpoint: str) -> Dict[str, Any]:
        """GET a non-paginated body (``client.get`` wraps it as ``{"results": [body]}``)."""
        data = self.client.get(endpoint)
        results = data.get("results") if isinstance(data, dict) else None
        return results[0] if results else data

    # ── list ──────────────────────────────────────────────────────────────────

    def get(self, project_slug: str, page: int = 1, page_size: int = 50, validate: bool = True,
            **filters: Any) -> PaginatedResult[ProjectDeployment]:
        """One page of the project's deployments. ``filters`` are sent as query parameters."""
        return super().get(
            query=filters or None, page=page, page_size=page_size, validate=validate,
            overwrite_endpoint=self._url(project_slug),
        )

    def where(self, project_slug: str, page_size: int = 50, validate: bool = True,
              **filters: Any) -> APIQuery[ProjectDeployment]:
        """Lazy iterator over the project's deployments."""
        return super().where(
            query=filters or None, page_size=page_size, validate=validate,
            overwrite_endpoint=self._url(project_slug),
        )

    def locations(self, project_slug: str, **filters: Any) -> list[ProjectLocation]:
        """The locations of the project's deployments, each with its deployment count."""
        self._ensure_supported()
        data = self.client.get(self._url(project_slug, "locations"), query=filters or None)
        return [ProjectLocation.model_validate(row) for row in data.get("results", [])]

    def find(self, project_slug: str, deployment_pk: int) -> ProjectDeploymentDetail:  # type: ignore[override]
        """The full, editable record of one deployment."""
        self._ensure_supported()
        return ProjectDeploymentDetail.model_validate(self._single(self._url(project_slug, deployment_pk)))

    # ── actions ───────────────────────────────────────────────────────────────

    def update(self, project_slug: str, deployment_pk: int, **fields: Any) -> ProjectDeploymentDetail:
        """Change some fields of a deployment (``PATCH``).

        Accepts the editable fields of :class:`~trapper_client.schemas.ProjectDeploymentDetail`
        (``comments``, ``camera_id``, ``camera_model``, ``camera_height``, ``habitat``, ``start_date``,
        ``end_date``, ``is_private``, ...). Needs ``can_update``. Note that the server may rewrite
        ``deployment_id`` when it saves.
        """
        self._ensure_supported()
        if not fields:
            raise ValueError("update() needs at least one field to change")
        response = self.client.make_request(self._url(project_slug, deployment_pk), "PATCH", body=fields)
        return ProjectDeploymentDetail.model_validate(response.json())

    def delete(self, project_slug: str, deployment_pk: int) -> None:
        """Delete a deployment (``DELETE``). Needs ``can_delete``; irreversible."""
        self._ensure_supported()
        self.client.make_request(self._url(project_slug, deployment_pk), "DELETE")

    def update_timestamps(self, project_slug: str, deployment_pk: int, time_offset: int) -> None:
        """Shift the ``date_recorded`` of every resource of the deployment by ``time_offset`` seconds.

        Fixes a camera clock that was wrong: use a negative value to go back. The classifications'
        dates are synchronised by a background task.
        """
        self._ensure_supported()
        self.client.make_request(
            self._url(project_slug, deployment_pk, "update_timestamps"), "PUT",
            body={"time_offset": int(time_offset)},
        )

    def progress(self, project_slug: str, deployment_pk: int) -> ProjectDeploymentProgress:
        """Per-stage AI pipeline progress of the deployment (``running`` is ``False`` when idle)."""
        self._ensure_supported()
        return ProjectDeploymentProgress.model_validate(
            self._single(self._url(project_slug, deployment_pk, "progress"))
        )

    # ── AI calibration (needs the project's AI models; not exercised against a live AI) ──

    def request_depth_calibration(
        self, project_slug: str, deployment_pk: int,
        calibration_ids: Iterable[int] | None = None,
        job_config_overrides: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Ask the AI pipeline to calibrate depth from the deployment's calibration samples.

        The reference points come from each sample's stored calibration data, not from this call.
        The project needs a depth AI model, otherwise the server answers ``400``.
        """
        self._ensure_supported()
        body: Dict[str, Any] = {}
        if calibration_ids is not None:
            body["calibration_ids"] = list(calibration_ids)
        if job_config_overrides:
            body["job_config_overrides"] = job_config_overrides
        return self.client.make_request(
            self._url(project_slug, deployment_pk, "depth-calibration"), "POST", body=body
        ).json()

    def request_distance_estimation(
        self, project_slug: str, deployment_pk: int, **payload: Any
    ) -> Dict[str, Any]:
        """Ask the AI pipeline to estimate animal distances for the deployment."""
        self._ensure_supported()
        return self.client.make_request(
            self._url(project_slug, deployment_pk, "estimate-distances"), "POST", body=payload
        ).json()

    def calibration_results(self, project_slug: str, deployment_pk: int) -> list[Dict[str, Any]]:
        """Results of the deployment's calibrations (raw rows; empty until a calibration ran)."""
        self._ensure_supported()
        data = self.client.get(self._url(project_slug, deployment_pk, "calibration-results"))
        return list(data.get("results", []))
