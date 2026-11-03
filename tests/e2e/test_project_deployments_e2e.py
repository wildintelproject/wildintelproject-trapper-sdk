"""
End-to-end tests for ProjectDeploymentsComponent (Trapper v2 ``api/deployments/<slug>/...``).

Requires: WILDINTEL_BASE_URL, WILDINTEL_ACCESS_TOKEN, WILDINTEL_SMOKE_ENABLED=1 and

    WILDINTEL_PROJECT_SLUG — slug of a classification project that is a Citizen Science project
                             (citizen_science_status public/private, with a classificator)

The tests that change data also need WILDINTEL_ALLOW_WRITE=1 and put back what they change. Trapper
rewrites ``deployment_id`` when a deployment is saved, so an ``update()`` leaves that field changed.
"""
from __future__ import annotations

import os

import pytest

from trapper_client import TrapperClient, err
from trapper_client.schemas import ProjectDeployment, ProjectDeploymentDetail, ProjectDeploymentProgress, ProjectLocation


@pytest.fixture(scope="module")
def client() -> TrapperClient:
    base_url = os.getenv("WILDINTEL_BASE_URL", "").strip()
    token = os.getenv("WILDINTEL_ACCESS_TOKEN", "").strip()
    if not base_url or not token:
        pytest.skip("Set WILDINTEL_BASE_URL and WILDINTEL_ACCESS_TOKEN")
    return TrapperClient(base_url=base_url, access_token=token,
                         verify_ssl=os.getenv("WILDINTEL_VERIFY_SSL", "1") not in ("0", "false"),
                         timeout=int(os.getenv("WILDINTEL_TIMEOUT", "30")))


@pytest.fixture(scope="module")
def slug(client) -> str:
    if client.server_version != "v2":
        pytest.skip("project deployments exist only in Trapper v2")
    value = os.getenv("WILDINTEL_PROJECT_SLUG", "").strip()
    if not value:
        pytest.skip("Set WILDINTEL_PROJECT_SLUG")
    return value


@pytest.fixture(scope="module")
def deployment_pk(client, slug) -> int:
    page = client.project_deployments.get(slug, page_size=1)
    if not page.results:
        pytest.skip("the project has no deployments")
    return page.results[0].pk


@pytest.mark.e2e
def test_v1_refuses(client):
    if client.server_version != "v1":
        pytest.skip("v1 only")
    with pytest.raises(err.UnsupportedVersionError):
        client.project_deployments.get("any")


@pytest.mark.e2e
def test_get_and_where(client, slug):
    page = client.project_deployments.get(slug, page_size=3)
    assert page.results and all(isinstance(d, ProjectDeployment) for d in page.results)
    assert len(page.results) <= 3 or page.pagination.page_size != 3   # the server may not paginate
    every = list(client.project_deployments.where(slug, page_size=2))
    assert len(every) == page.pagination.count


@pytest.mark.e2e
def test_locations(client, slug):
    rows = client.project_deployments.locations(slug)
    assert rows and all(isinstance(r, ProjectLocation) for r in rows)
    assert sum(r.deployments_count for r in rows) >= 1


@pytest.mark.e2e
def test_find_matches_the_listing(client, slug, deployment_pk):
    detail = client.project_deployments.find(slug, deployment_pk)
    assert isinstance(detail, ProjectDeploymentDetail)
    assert detail.pk == deployment_pk and detail.location_id is not None


@pytest.mark.e2e
def test_progress_and_calibration_results(client, slug, deployment_pk):
    progress = client.project_deployments.progress(slug, deployment_pk)
    assert isinstance(progress, ProjectDeploymentProgress) and progress.pk == deployment_pk
    assert isinstance(client.project_deployments.calibration_results(slug, deployment_pk), list)


@pytest.mark.e2e
def test_unknown_project_is_not_found(client, slug):
    with pytest.raises(err.NotFoundError):
        client.project_deployments.get("no-such-project-slug")


@pytest.fixture
def may_write():
    if os.getenv("WILDINTEL_ALLOW_WRITE", "").strip() != "1":
        pytest.skip("Set WILDINTEL_ALLOW_WRITE=1 to run the tests that change data")


@pytest.mark.e2e
def test_update_timestamps_round_trip(client, slug, deployment_pk, may_write):
    before = client.project_deployments.find(slug, deployment_pk)
    client.project_deployments.update_timestamps(slug, deployment_pk, time_offset=60)
    client.project_deployments.update_timestamps(slug, deployment_pk, time_offset=-60)
    after = client.project_deployments.find(slug, deployment_pk)
    assert after.start_date == before.start_date


@pytest.mark.e2e
def test_update_comments_round_trip(client, slug, deployment_pk, may_write):
    original = client.project_deployments.find(slug, deployment_pk).comments
    try:
        changed = client.project_deployments.update(slug, deployment_pk, comments="sdk e2e")
        assert changed.comments == "sdk e2e"
    finally:
        client.project_deployments.update(slug, deployment_pk, comments=original or "")
    assert client.project_deployments.find(slug, deployment_pk).comments == (original or "")


@pytest.mark.e2e
def test_update_to_nothing_is_refused_before_any_request(client, slug, deployment_pk):
    with pytest.raises(ValueError):
        client.project_deployments.update(slug, deployment_pk)
