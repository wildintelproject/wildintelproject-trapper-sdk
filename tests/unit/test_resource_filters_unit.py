"""Resource list filters: lists in the form Trapper reads, and a warning for the ones it ignores."""
from __future__ import annotations

import warnings
from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import paginated_response
from trapper_client import err
from trapper_client.components.resources import ResourcesComponent


def make(version="v1"):
    client = MagicMock()
    client.server_version = version
    client.get.return_value = paginated_response([])
    client.get_all.return_value = paginated_response([])
    return ResourcesComponent(client), client


def sent(client):
    return client.get.call_args.kwargs["query"]


def caught(func, *args, **kwargs):
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        func(*args, **kwargs)
    return [w for w in record if issubclass(w.category, err.UnknownFilterWarning)]


class TestLists:

    @pytest.mark.parametrize("name", ["collections", "deployments", "tags", "species"])
    @pytest.mark.parametrize("value, expected", [
        ([2, 3], [2, 3]),
        ((2, 3), [2, 3]),
        ("2,3", ["2", "3"]),
        (" 2 , 3 ", ["2", "3"]),
        ("2", ["2"]),
        (2, [2]),
        ("2,,3,", ["2", "3"]),
        ([], []),
        ("", []),
    ])
    def test_repeated_filters_go_as_a_list(self, name, value, expected):
        comp, client = make()
        comp.get(**{name: value})
        assert sent(client)[name] == expected

    @pytest.mark.parametrize("name", ["pk", "locations_map"])
    @pytest.mark.parametrize("value, expected", [
        ([2, 3], "2,3"),
        ((2, 3), "2,3"),
        ("2,3", "2,3"),
        (" 2 , 3 ", "2,3"),
        (5, "5"),
        ("5", "5"),
        ([], ""),
    ])
    def test_comma_filters_go_as_one_string(self, name, value, expected):
        comp, client = make()
        comp.get(**{name: value})
        assert sent(client)[name] == expected

    def test_none_and_other_filters_are_left_alone(self):
        comp, client = make()
        comp.get(collections=None, status="Public", owner=True, search="a,b", resource_type="I")
        q = sent(client)
        assert q["collections"] is None and q["status"] == "Public" and q["owner"] is True and q["search"] == "a,b"

    @pytest.mark.parametrize("method", ["get", "get_all", "where", "export"])
    def test_every_way_of_listing_normalizes(self, method):
        comp, client = make()
        if method == "where":
            q = comp.where(deployments="1,2", pk=[1, 2]).query
        else:
            getattr(comp, method)(**({"file": None} if method == "export" else {}), deployments="1,2", pk=[1, 2])
            q = (client.get_all if method in ("get_all", "export") else client.get).call_args.kwargs["query"]
        assert q["deployments"] == ["1", "2"] and q["pk"] == "1,2"

    def test_the_query_dict_is_normalized_too(self):
        comp, client = make()
        comp.get(query={"collections": "2,3"})
        assert sent(client)["collections"] == ["2", "3"]


class TestWarning:

    @pytest.mark.parametrize("version", ["v1", "v2"])
    def test_what_the_server_applies_does_not_warn(self, version):
        comp, _ = make(version)
        assert caught(
            comp.get, page=1, page_size=5, pk=1, resource_type="I", status="Public", rdate_from="2024-01-01",
            rdate_to="2024-02-01", udate_from="2024-01-01", udate_to="2024-02-01", rtime_from="10:00",
            rtime_to="12:00", owner=True, collections=[1], deployments=[1], tags=[1], observation_type="animal",
            species=[1], timestamp_error=True, search="x", name="n", token="t",
        ) == []

    @pytest.mark.parametrize("version", ["v1", "v2"])
    @pytest.mark.parametrize("name", ["ordering", "in_bbox", "foo", "radius", "colls"])
    def test_what_it_ignores_warns(self, version, name):
        comp, _ = make(version)
        found = caught(comp.get, **{name: "x"})
        assert len(found) == 1 and repr(name) in str(found[0].message)

    def test_locations_map_is_applied_by_v1_only(self):
        assert caught(make("v1")[0].get, locations_map=1) == []
        assert len(caught(make("v2")[0].get, locations_map=1)) == 1

    @pytest.mark.parametrize("version", ["v1", "v2"])
    def test_deployment_isnull_is_named_as_a_server_error(self, version):
        comp, client = make(version)
        found = caught(comp.get, deployment__isnull=True)
        assert len(found) == 1 and "500" in str(found[0].message) and "'deployment__isnull'" in str(found[0].message)
        assert sent(client)["deployment__isnull"] is True          # still sent

    def test_deployment_isnull_does_not_learn_the_version(self):
        client = MagicMock()
        type(client).server_version = property(lambda self: pytest.fail("version probed"))
        client.get.return_value = paginated_response([])
        assert len(caught(ResourcesComponent(client).get, deployment__isnull=True)) == 1

    def test_common_filters_do_not_learn_the_version(self):
        client = MagicMock()
        type(client).server_version = property(lambda self: pytest.fail("version probed"))
        client.get.return_value = paginated_response([])
        ResourcesComponent(client).get(collections="1,2", status="Public", page_size=5)

    def test_the_scoped_endpoints_are_checked_too(self):
        comp, _ = make("v1")
        assert len(caught(comp.get_by_collection, 5, bogus=1)) == 1
