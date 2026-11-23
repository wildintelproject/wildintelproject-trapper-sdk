"""ProjectDeploymentsComponent (Trapper v2 ``api/deployments/<slug>/...``) against a mocked client."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from trapper_client import err
from trapper_client.components.project_deployments import ProjectDeploymentsComponent
from trapper_client.schemas import ProjectDeployment, ProjectDeploymentDetail, ProjectDeploymentProgress, ProjectLocation

SLUG = "mamiferos-donana-sm"


def component(version="v2"):
    client = MagicMock()
    client.server_version = version
    return ProjectDeploymentsComponent(client), client


LIST_ROW = {
    "pk": 3, "deployment_id": "don01-2024a", "deployment_code": "don01-2024a",
    "location_name": "Doñana", "start_date": "2024-03-01T10:00:00+01:00",
    "end_date": "2024-04-15T09:30:00+02:00", "sequences": 0,
    "owner": {"id": 1, "name": "sdktest", "avatar": ""},
    "thumbnails": [{"pk": 6, "thumbnail": "/storage/resource/media/5/tfile/?is_cs=1"}],
    "species": [{"total": 1, "latin_name": "Lynx pardinus", "english_name": "Iberian Lynx"}],
    "can_update": True, "can_delete": False,
}
DETAIL = {**LIST_ROW, "location_id": 5, "location": {"name": "Doñana", "latitude": 37.05, "longitude": -6.44},
          "camera_id": "CT-1001", "camera_height": "0.45", "bait_type": 1, "feature_type": "none",
          "timestamp_issues": False, "comments": "Primera", "is_private": True, "is_incomplete": False,
          "resources_count": 5, "media": [], "media_state": {}}


class TestReads:
    def test_get_parses_the_listing(self):
        comp, client = component()
        client.get.return_value = {"pagination": {"page": 1, "page_size": 10, "pages": 1, "count": 1}, "results": [LIST_ROW]}

        page = comp.get(SLUG, page_size=10)

        assert client.get.call_args.args[0] == f"api/deployments/{SLUG}/"
        assert isinstance(page.results[0], ProjectDeployment)
        assert page.results[0].species[0].latin_name == "Lynx pardinus"

    def test_filters_are_sent_as_query(self):
        comp, client = component()
        client.get.return_value = {"results": []}

        comp.get(SLUG, search="don01")

        assert client.get.call_args.kwargs["query"]["search"] == "don01"

    def test_find_unwraps_the_single_body(self):
        comp, client = component()
        client.get.return_value = {"pagination": {}, "results": [DETAIL]}

        dep = comp.find(SLUG, 3)

        assert client.get.call_args.args[0] == f"api/deployments/{SLUG}/3/"
        assert isinstance(dep, ProjectDeploymentDetail) and dep.camera_id == "CT-1001"

    def test_locations(self):
        comp, client = component()
        client.get.return_value = {"results": [{"pk": 5, "name": "Doñana", "latitude": 37.05, "longitude": -6.44, "deployments_count": 2}]}

        rows = comp.locations(SLUG)

        assert isinstance(rows[0], ProjectLocation) and rows[0].deployments_count == 2

    def test_progress(self):
        comp, client = component()
        client.get.return_value = {"results": [{"pk": 3, "deployment_id": "d", "running": False, "stages": []}]}

        progress = comp.progress(SLUG, 3)

        assert client.get.call_args.args[0] == f"api/deployments/{SLUG}/3/progress/"
        assert isinstance(progress, ProjectDeploymentProgress) and progress.running is False

    def test_calibration_results(self):
        comp, client = component()
        client.get.return_value = {"pagination": {"count": 0}, "results": []}

        assert comp.calibration_results(SLUG, 3) == []


class TestActions:
    def test_update_patches_only_the_given_fields(self):
        comp, client = component()
        client.make_request.return_value.json.return_value = DETAIL

        dep = comp.update(SLUG, 3, comments="moved")

        client.make_request.assert_called_once_with(f"api/deployments/{SLUG}/3/", "PATCH", body={"comments": "moved"})
        assert dep.comments == "Primera"

    def test_update_without_fields_is_refused(self):
        comp, _ = component()
        with pytest.raises(ValueError):
            comp.update(SLUG, 3)

    def test_delete(self):
        comp, client = component()

        comp.delete(SLUG, 3)

        client.make_request.assert_called_once_with(f"api/deployments/{SLUG}/3/", "DELETE")

    def test_update_timestamps_sends_the_offset_in_seconds(self):
        comp, client = component()

        comp.update_timestamps(SLUG, 3, time_offset=-3600)

        client.make_request.assert_called_once_with(
            f"api/deployments/{SLUG}/3/update_timestamps/", "PUT", body={"time_offset": -3600})

    def test_depth_calibration_body(self):
        comp, client = component()
        client.make_request.return_value.json.return_value = {"ok": True}

        comp.request_depth_calibration(SLUG, 3, calibration_ids=[1, 2], job_config_overrides={"fit_method": "x"})

        assert client.make_request.call_args.kwargs["body"] == {
            "calibration_ids": [1, 2], "job_config_overrides": {"fit_method": "x"}}

    def test_distance_estimation(self):
        comp, client = component()
        client.make_request.return_value.json.return_value = {}

        comp.request_distance_estimation(SLUG, 3)

        assert client.make_request.call_args.args[:2] == (f"api/deployments/{SLUG}/3/estimate-distances/", "POST")


@pytest.mark.parametrize("call", [
    lambda c: c.get(SLUG), lambda c: c.where(SLUG), lambda c: c.find(SLUG, 1),
    lambda c: c.locations(SLUG), lambda c: c.update(SLUG, 1, comments="x"),
    lambda c: c.delete(SLUG, 1), lambda c: c.update_timestamps(SLUG, 1, 0),
    lambda c: c.progress(SLUG, 1), lambda c: c.calibration_results(SLUG, 1),
    lambda c: c.request_depth_calibration(SLUG, 1), lambda c: c.request_distance_estimation(SLUG, 1),
])
def test_everything_is_refused_on_v1(call):
    comp, _ = component("v1")
    with pytest.raises(err.UnsupportedVersionError):
        call(comp)
