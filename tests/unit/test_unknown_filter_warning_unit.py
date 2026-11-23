"""``UnknownFilterWarning``: Trapper ignores a filter it does not know, so the SDK says so."""
from __future__ import annotations

import warnings
from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import paginated_response
from trapper_client import err
from trapper_client.components.locations import LocationsComponent


def make(version):
    client = MagicMock()
    client.server_version = version
    client.get.return_value = paginated_response([])
    client.get_all.return_value = paginated_response([])
    return LocationsComponent(client), client


def caught(func, *args, **kwargs):
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        func(*args, **kwargs)
    return [w for w in record if issubclass(w.category, err.UnknownFilterWarning)]


class TestWarning:

    @pytest.mark.parametrize("version", ["v1", "v2"])
    @pytest.mark.parametrize("method", ["get", "get_all", "where", "all", "export"])
    def test_every_way_of_listing_warns(self, version, method):
        comp, _ = make(version)
        found = caught(getattr(comp, method), bogus="x")
        assert len(found) == 1
        assert "'bogus'" in str(found[0].message)

    def test_names_all_the_unknown_ones_sorted(self):
        comp, _ = make("v1")
        found = caught(comp.get, zeta=1, alpha=2, name="ok")
        assert "'alpha', 'zeta'" in str(found[0].message)
        assert "'name'" not in str(found[0].message).split("ignores")[1].split("returns")[0]

    def test_query_dict_is_checked_too(self):
        comp, _ = make("v1")
        assert len(caught(comp.get, query={"bogus": 1})) == 1

    def test_request_is_still_made_with_the_filter(self):
        comp, client = make("v1")
        caught(comp.get, bogus="x")
        assert client.get.call_args.kwargs["query"]["bogus"] == "x"

    def test_warning_points_at_the_caller(self):
        comp, _ = make("v1")
        for call in (lambda: comp.get(bogus=1), lambda: comp.where(bogus=1)):
            with warnings.catch_warnings(record=True) as record:
                warnings.simplefilter("always")
                call()
            assert record and record[0].filename == __file__

    def test_it_is_a_userwarning_that_can_be_silenced(self):
        assert issubclass(err.UnknownFilterWarning, UserWarning)
        comp, _ = make("v1")
        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("ignore", err.UnknownFilterWarning)
            comp.get(bogus=1)
        assert record == []


class TestNoWarning:

    @pytest.mark.parametrize("version", ["v1", "v2"])
    def test_filters_the_server_applies(self, version):
        comp, _ = make(version)
        assert caught(
            comp.get, page=1, page_size=10, pk=1, name="a", description="b", owner=True, owners=[1],
            research_project=1, deployments=1, search="x", location_id="a", is_public=True,
            ignore_DST=False, coordinate_uncertainty=10, date_created="2020-01-01", managers=1,
            research_projects_member=1,
        ) == []

    def test_no_filters_no_warning(self):
        comp, _ = make("v1")
        assert caught(comp.get) == []

    def test_a_component_without_known_filters_never_warns(self):
        comp, _ = make("v1")
        comp.known_filters = None
        assert caught(comp.get, bogus=1) == []


class TestByVersion:

    def test_in_bbox_is_applied_by_v2_only(self):
        assert caught(make("v2")[0].get, in_bbox="0,0,1,1") == []
        assert len(caught(make("v1")[0].get, in_bbox="0,0,1,1")) == 1

    def test_radius_and_ordering_are_ignored_by_both(self):
        for version in ("v1", "v2"):
            found = caught(make(version)[0].get, radius="0,0,1", ordering="name")
            assert len(found) == 1 and "'ordering', 'radius'" in str(found[0].message)

    @pytest.mark.parametrize("name", ["locations_map", "country", "state", "county", "city"])
    def test_v1_only_filters(self, name):
        assert caught(make("v1")[0].get, **{name: "x"}) == []
        assert len(caught(make("v2")[0].get, **{name: "x"})) == 1


class TestInArea:

    def test_in_area_warns_about_a_wrong_filter_not_about_the_area(self):
        comp, _ = make("v1")
        found = caught(lambda: list(comp.in_area(bbox=(0, 0, 1, 1), bogus=1)))
        assert len(found) == 1 and "'bogus'" in str(found[0].message)
        assert caught(lambda: list(comp.in_area(bbox=(0, 0, 1, 1), research_project=1))) == []


class TestVersionProbe:

    def test_common_filters_do_not_learn_the_server_version(self):
        client = MagicMock()
        type(client).server_version = property(lambda self: pytest.fail("version probed"))
        client.get.return_value = paginated_response([])
        LocationsComponent(client).get(name="a", research_project=1, page_size=5)
