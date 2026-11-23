"""Collection list filters: lists in the form Trapper reads, a validated ``status``, and a warning for the rest."""
from __future__ import annotations

import warnings
from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import paginated_response
from trapper_client import CollectionStatus, err
from trapper_client.components.collections import CollectionsComponent


def make(version="v1"):
    client = MagicMock()
    client.server_version = version
    client.get.return_value = paginated_response([])
    client.get_all.return_value = paginated_response([])
    return CollectionsComponent(client), client


def sent(client):
    return client.get.call_args.kwargs["query"]


def caught(func, *args, **kwargs):
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        func(*args, **kwargs)
    return [w for w in record if issubclass(w.category, err.UnknownFilterWarning)]


class TestLists:

    @pytest.mark.parametrize("name", ["owners", "research_projects"])
    @pytest.mark.parametrize("value, expected", [
        ([1, 2], [1, 2]), ((1, 2), [1, 2]), ("1,2", ["1", "2"]), (" 1 , 2 ", ["1", "2"]), (3, [3]), ("", []),
    ])
    def test_repeated_filters_go_as_a_list(self, name, value, expected):
        comp, client = make()
        comp.get(**{name: value})
        assert sent(client)[name] == expected

    @pytest.mark.parametrize("name", ["pk", "locations_map"])
    @pytest.mark.parametrize("value, expected", [
        ([2, 1], "2,1"), ((2, 1), "2,1"), ("2,1", "2,1"), (" 2 , 1 ", "2,1"), (5, "5"),
    ])
    def test_comma_filters_go_as_one_string(self, name, value, expected):
        comp, client = make()
        comp.get(**{name: value})
        assert sent(client)[name] == expected

    @pytest.mark.parametrize("method", ["get", "get_all", "where"])
    def test_every_way_of_listing_normalizes(self, method):
        comp, client = make()
        if method == "where":
            q = comp.where(pk=[1, 2], status="public").query
        else:
            getattr(comp, method)(pk=[1, 2], status="public")
            q = (client.get_all if method == "get_all" else client.get).call_args.kwargs["query"]
        assert q["pk"] == "1,2" and q["status"] == "Public"

    def test_the_sub_endpoints_normalize_too(self):
        comp, client = make()
        comp.get_map(pk=[1, 2])
        assert sent(client)["pk"] == "1,2"
        comp.get_append(status="archived")
        assert sent(client)["status"] == "Archived"


class TestStatus:

    @pytest.mark.parametrize("value, expected", [
        ("Private", "Private"), ("private", "Private"), ("PRIVATE", "Private"), (" public ", "Public"),
        ("OnDemand", "OnDemand"), ("ondemand", "OnDemand"), ("On demand", "OnDemand"), ("on_demand", "OnDemand"),
        ("archived", "Archived"), (CollectionStatus.PUBLIC, "Public"),
    ])
    def test_any_case_is_resolved_to_what_trapper_stores(self, value, expected):
        comp, client = make()
        comp.get(status=value)
        assert sent(client)["status"] == expected

    @pytest.mark.parametrize("value", ["Bogus", "", "privat", 3, True])
    def test_an_unknown_status_is_refused_before_any_request(self, value):
        comp, client = make()
        with pytest.raises(ValueError, match="Private, OnDemand, Public, Archived"):
            comp.get(status=value)
        client.get.assert_not_called()

    def test_no_status_is_left_alone(self):
        comp, client = make()
        comp.get(name="x")
        assert "status" not in sent(client)
        comp.get(status=None)
        assert sent(client)["status"] is None

    def test_the_enum(self):
        assert [m.value for m in CollectionStatus] == ["Private", "OnDemand", "Public", "Archived"]
        assert CollectionStatus.ON_DEMAND.label == "On demand"
        assert CollectionStatus.parse("on demand") is CollectionStatus.ON_DEMAND
        assert CollectionStatus.PUBLIC == "Public"            # a str: it can be sent as it is


class TestWarning:

    @pytest.mark.parametrize("version", ["v1", "v2"])
    def test_what_the_server_applies_does_not_warn(self, version):
        comp, _ = make(version)
        assert caught(
            comp.get, page=1, page_size=5, pk=1, status="Public", owner=True, owners=[1], research_projects=[1],
            search="x", name="n", period_begin="2024-01-01", period_end="2024-12-31", cs_deployment=1,
            is_complete_cs_collection=True, managers=[1], members=[1],
        ) == []

    @pytest.mark.parametrize("version", ["v1", "v2"])
    @pytest.mark.parametrize("name", ["ordering", "in_bbox", "foo", "description", "date_created"])
    def test_what_it_ignores_warns(self, version, name):
        comp, _ = make(version)
        found = caught(comp.get, **{name: "x"})
        assert len(found) == 1 and repr(name) in str(found[0].message)

    def test_locations_map_is_applied_by_v1_only(self):
        assert caught(make("v1")[0].get, locations_map=1) == []
        assert len(caught(make("v2")[0].get, locations_map=1)) == 1

    def test_common_filters_do_not_learn_the_version(self):
        client = MagicMock()
        type(client).server_version = property(lambda self: pytest.fail("version probed"))
        client.get.return_value = paginated_response([])
        CollectionsComponent(client).get(pk="1,2", status="public", owner=True, page_size=5)
