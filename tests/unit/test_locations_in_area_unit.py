"""``client.locations.in_area()``: filter the locations by area on the client."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from trapper_client import Location
from trapper_client.components.locations import LocationsComponent
from trapper_client.geo import distance_m, in_bbox

# Doñana (Spain), Madrid, Sevilla, Oslo, a point on each side of the antimeridian, one with no coordinates
LOCATIONS = [
    Location(pk=1, name="donana", coordinates="-6.44, 37.05"),
    Location(pk=2, name="madrid", coordinates="-3.70, 40.42"),
    Location(pk=3, name="sevilla", coordinates="-5.98, 37.39"),
    Location(pk=4, name="oslo", coordinates="10.75, 59.91"),
    Location(pk=5, name="fiji-east", coordinates="179.5, -17.0"),
    Location(pk=6, name="fiji-west", coordinates="-179.5, -17.0"),
    Location(pk=7, name="nowhere", coordinates=None),
    Location(pk=8, name="broken", coordinates="not a point"),
]


@pytest.fixture
def component():
    comp = LocationsComponent(MagicMock())
    calls = []

    def where(query=None, filter_fn=None, **kwargs):
        calls.append(kwargs)
        return iter([loc for loc in LOCATIONS if filter_fn is None or filter_fn(loc)])

    comp.where = where
    comp.calls = calls
    return comp


def names(items):
    return [loc.name for loc in items]


class TestGeo:

    def test_distance_zero_and_known(self):
        assert distance_m(-6.44, 37.05, -6.44, 37.05) == 0
        # Madrid - Sevilla is about 391 km in a straight line
        assert 385_000 < distance_m(-3.70, 40.42, -5.98, 37.39) < 395_000
        # one degree of latitude is about 111.2 km
        assert distance_m(0, 0, 0, 1) == pytest.approx(111_195, rel=1e-3)

    def test_distance_across_antimeridian_is_short(self):
        assert distance_m(179.5, 0, -179.5, 0) == pytest.approx(111_195, rel=1e-3)

    def test_bbox_edges_are_inside(self):
        assert in_bbox(0, 0, (0, 0, 1, 1))
        assert in_bbox(1, 1, (0, 0, 1, 1))
        assert not in_bbox(1.0001, 1, (0, 0, 1, 1))
        assert not in_bbox(0.5, 1.5, (0, 0, 1, 1))

    def test_bbox_across_antimeridian(self):
        box = (170, -20, -170, -10)
        assert in_bbox(179.5, -17, box) and in_bbox(-179.5, -17, box)
        assert not in_bbox(0, -17, box)


class TestInArea:

    def test_bbox(self, component):
        found = component.in_area(bbox=(-7, 36, -5, 38))
        assert names(found) == ["donana", "sevilla"]

    def test_circle(self, component):
        found = component.in_area(center=(-6.44, 37.05), radius=70_000)
        assert names(found) == ["donana", "sevilla"]
        assert names(component.in_area(center=(-6.44, 37.05), radius=10)) == ["donana"]

    def test_radius_zero_finds_the_exact_point(self, component):
        assert names(component.in_area(center=(-6.44, 37.05), radius=0)) == ["donana"]

    def test_bbox_and_circle_must_both_hold(self, component):
        found = component.in_area(bbox=(-7, 36, -6.2, 38), center=(-6.44, 37.05), radius=100_000)
        assert names(found) == ["donana"]

    def test_antimeridian(self, component):
        assert names(component.in_area(bbox=(170, -20, -170, -10))) == ["fiji-east", "fiji-west"]
        assert names(component.in_area(center=(179.9, -17), radius=200_000)) == ["fiji-east", "fiji-west"]

    def test_locations_without_readable_coordinates_are_left_out(self, component):
        found = component.in_area(bbox=(-180, -90, 180, 90))
        assert names(found) == ["donana", "madrid", "sevilla", "oslo", "fiji-east", "fiji-west"]

    def test_other_filters_go_to_the_server(self, component):
        list(component.in_area(bbox=(-7, 36, -5, 38), research_project=3, search="x"))
        assert component.calls == [{"research_project": 3, "search": "x"}]

    def test_returns_an_iterator_of_locations(self, component):
        found = component.in_area(bbox=(-7, 36, -5, 38))
        assert all(isinstance(loc, Location) for loc in found)

    @pytest.mark.parametrize("kwargs", [
        {},
        {"center": (0, 0)},
        {"radius": 10},
        {"bbox": (0, 0, 1)},
        {"bbox": (0, 0, 1, 95)},
        {"bbox": (0, 0, 190, 1)},
        {"bbox": (0, 10, 1, 5)},
        {"center": (200, 0), "radius": 10},
        {"center": (0, 0, 0), "radius": 10},
        {"center": (0, 0), "radius": -1},
    ])
    def test_invalid_area_raises_before_any_request(self, component, kwargs):
        with pytest.raises(ValueError):
            component.in_area(**kwargs)
        assert component.calls == []


class TestServerSideBox:
    """Trapper v2 applies ``in_bbox`` in its list: the box is sent so fewer pages are read."""

    def with_version(self, component, version):
        component.client.server_version = version
        return component

    def test_v2_sends_the_box(self, component):
        found = self.with_version(component, "v2").in_area(bbox=(-7, 36, -5, 38))
        assert component.calls == [{"in_bbox": "-7.0,36.0,-5.0,38.0"}]
        assert names(found) == ["donana", "sevilla"]           # still filtered on the client

    def test_v1_does_not_send_it(self, component):
        list(self.with_version(component, "v1").in_area(bbox=(-7, 36, -5, 38)))
        assert component.calls == [{}]

    def test_a_box_across_the_antimeridian_is_not_sent(self, component):
        list(self.with_version(component, "v2").in_area(bbox=(170, -20, -170, -10)))
        assert component.calls == [{}]

    def test_a_circle_alone_is_not_sent(self, component):
        list(self.with_version(component, "v2").in_area(center=(-6.44, 37.05), radius=1000))
        assert component.calls == [{}]

    def test_other_filters_are_kept_and_a_given_in_bbox_wins(self, component):
        list(self.with_version(component, "v2").in_area(bbox=(-7, 36, -5, 38), research_project=3))
        list(self.with_version(component, "v2").in_area(bbox=(-7, 36, -5, 38), in_bbox="0,0,1,1"))
        assert component.calls == [
            {"research_project": 3, "in_bbox": "-7.0,36.0,-5.0,38.0"},
            {"in_bbox": "0,0,1,1"},
        ]
