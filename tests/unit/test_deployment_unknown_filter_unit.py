"""``UnknownFilterWarning`` on the deployments list (see also the locations one)."""
from __future__ import annotations

import warnings
from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import paginated_response
from trapper_client import err
from trapper_client.components.deployments import DeploymentsComponent


def make(version):
    client = MagicMock()
    client.server_version = version
    client.get.return_value = paginated_response([])
    client.get_all.return_value = paginated_response([])
    return DeploymentsComponent(client)


def caught(func, *args, **kwargs):
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        func(*args, **kwargs)
    return [w for w in record if issubclass(w.category, err.UnknownFilterWarning)]


@pytest.mark.parametrize("version", ["v1", "v2"])
@pytest.mark.parametrize("name", ["colls", "collections", "ordering", "radius", "bait_use", "foo"])
def test_filters_the_server_ignores_warn(version, name):
    found = caught(make(version).get, **{name: "x"})
    assert len(found) == 1 and repr(name) in str(found[0].message)


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_filters_the_server_applies_do_not_warn(version):
    assert caught(
        make(version).get, page=1, page_size=5, location=1, research_project=2, tags=3, owner=True,
        sdate_from="2024-01-01", sdate_to="2024-12-31", edate_from="2024-01-01", edate_to="2024-12-31",
        classification_project=1, correct_setup=True, correct_tstamp=True, search="x", deployment_id="a",
        setup_by="x", camera_id="x", habitat="x", session="s", array="a", comments="c", is_incomplete=False,
    ) == []


def test_in_bbox_is_applied_by_v2_only():
    assert caught(make("v2").get, in_bbox="0,0,1,1") == []
    assert len(caught(make("v1").get, in_bbox="0,0,1,1")) == 1


def test_where_and_export_warn_too():
    assert len(caught(make("v1").where, colls=1)) == 1
    assert len(caught(make("v1").export, file=None, colls=1)) == 1


def test_by_collection_is_the_way_and_does_not_warn():
    comp = make("v1")
    comp.client.get.return_value = paginated_response([])
    assert caught(comp.by_collection, 5, research_project=3) == []


def test_common_filters_do_not_learn_the_server_version():
    client = MagicMock()
    type(client).server_version = property(lambda self: pytest.fail("version probed"))
    client.get.return_value = paginated_response([])
    DeploymentsComponent(client).get(research_project=1, page_size=5)
