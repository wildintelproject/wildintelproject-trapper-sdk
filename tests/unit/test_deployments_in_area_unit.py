"""``deployments.in_area()``: the deployments whose location is inside an area."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from trapper_client import Deployment, Location
from trapper_client.components.deployments import DeploymentsComponent

LOCATIONS = [
    Location(pk=1, name="donana", coordinates="-6.44, 37.05"),
    Location(pk=2, name="madrid", coordinates="-3.70, 40.42"),
    Location(pk=3, name="sevilla", coordinates="-5.98, 37.39"),
    Location(pk=4, name="nowhere", coordinates=None),
]
DEPLOYMENTS = [Deployment(pk=i, deployment_id=f"d{i}", location=loc) for i, loc in
               ((10, 1), (11, 1), (12, 2), (13, 3), (14, 4))]


@pytest.fixture
def component(monkeypatch):
    client = MagicMock()
    client.server_version = "v1"
    comp = DeploymentsComponent(client)
    comp.calls = []

    # the locations of the server, listed page by page, as LocationsComponent.where does
    monkeypatch.setattr(
        "trapper_client.components.locations.LocationsComponent.where",
        lambda self, query=None, filter_fn=None, **kw: iter([l for l in LOCATIONS if filter_fn is None or filter_fn(l)]),
    )

    def where(query=None, **kwargs):
        comp.calls.append(kwargs)
        wanted = set(kwargs.get("location", []))
        return iter([d for d in DEPLOYMENTS if d.location in wanted])

    comp.where = where
    return comp


def ids(items):
    return [d.deployment_id for d in items]


class TestInArea:

    def test_bbox(self, component):
        assert ids(component.in_area(bbox=(-7, 36, -5, 38))) == ["d10", "d11", "d13"]

    def test_circle(self, component):
        assert ids(component.in_area(center=(-6.44, 37.05), radius=1000)) == ["d10", "d11"]

    def test_locations_without_coordinates_are_left_out(self, component):
        assert "d14" not in ids(component.in_area(bbox=(-180, -90, 180, 90)))

    def test_empty_area_makes_no_deployment_request(self, component):
        assert list(component.in_area(bbox=(100, 0, 101, 1))) == []
        assert component.calls == []

    def test_the_locations_go_to_the_server_as_pks(self, component):
        list(component.in_area(bbox=(-7, 36, -5, 38)))
        assert component.calls == [{"location": [1, 3]}]

    def test_filters_are_for_the_deployments(self, component):
        list(component.in_area(bbox=(-7, 36, -5, 38), research_project=3, tags=2))
        assert component.calls == [{"location": [1, 3], "research_project": 3, "tags": 2}]

    def test_pks_go_in_batches(self, component):
        component.in_area_batch_size = 1
        found = ids(component.in_area(bbox=(-7, 36, -5, 38)))
        assert component.calls == [{"location": [1]}, {"location": [3]}]
        assert found == ["d10", "d11", "d13"]

    def test_is_lazy_about_the_deployments(self, component):
        it = component.in_area(bbox=(-7, 36, -5, 38))
        assert component.calls == []
        next(it)
        assert component.calls == [{"location": [1, 3]}]

    @pytest.mark.parametrize("kwargs", [
        {}, {"center": (0, 0)}, {"radius": 5}, {"bbox": (0, 0, 1)}, {"bbox": (0, 10, 1, 5)},
        {"center": (200, 0), "radius": 5},
    ])
    def test_a_wrong_area_raises_at_the_call(self, component, kwargs):
        with pytest.raises(ValueError):
            component.in_area(**kwargs)
        assert component.calls == []

    def test_location_cannot_be_combined(self, component):
        with pytest.raises(ValueError, match="location"):
            component.in_area(bbox=(0, 0, 1, 1), location=[1])
