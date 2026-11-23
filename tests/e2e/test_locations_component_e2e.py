"""
End-to-end tests for LocationsComponent.

Requires environment variables:
    WILDINTEL_BASE_URL, WILDINTEL_ACCESS_TOKEN, WILDINTEL_SMOKE_ENABLED=1

Optional:
    WILDINTEL_LOCATION_PK — pk of an existing location (for find tests)
"""
import pytest

from tests.base_component_tests import ComponentE2ETestBase
from trapper_client.components.locations import LocationsComponent
from trapper_client.schemas import Location, LocationExport


class TestLocationsComponentE2E(ComponentE2ETestBase):
    component_class = LocationsComponent
    schema = Location
    export_schema = LocationExport
    env_pk_var = "WILDINTEL_LOCATION_PK"

    @pytest.mark.e2e
    def test_locations_have_numeric_longitude_and_latitude(self, component):
        """The coordinates string of the list is read as numbers, on Trapper v1 and v2."""
        page = component.get(page=1, page_size=25)
        located = [loc for loc in page.results if loc.coordinates]
        if not located:
            pytest.skip("No location with coordinates on this server")
        for loc in located:
            assert isinstance(loc.longitude, float) and -180 <= loc.longitude <= 180, loc.coordinates
            assert isinstance(loc.latitude, float) and -90 <= loc.latitude <= 90, loc.coordinates

    @pytest.mark.e2e
    def test_in_area_filters_on_the_client(self, component):
        """``in_area`` keeps what the list would not filter, on Trapper v1 and v2."""
        everything = [loc for loc in component.where(page_size=100) if loc.longitude is not None]
        if not everything:
            pytest.skip("No location with coordinates on this server")
        target = everything[0]
        lon, lat = target.longitude, target.latitude

        box = (lon - 0.001, lat - 0.001, lon + 0.001, lat + 0.001)
        in_box = list(component.in_area(bbox=box, page_size=100))
        assert target.pk in {loc.pk for loc in in_box}
        assert all(box[0] <= loc.longitude <= box[2] and box[1] <= loc.latitude <= box[3] for loc in in_box)

        around = list(component.in_area(center=(lon, lat), radius=1, page_size=100))
        assert target.pk in {loc.pk for loc in around}

        # a box on the other side of the Earth is empty, whereas the server's own list ignores `in_bbox`
        far = (lon + 90 if lon <= 0 else lon - 90, -1.0, lon + 91 if lon <= 0 else lon - 89, 1.0)
        assert [loc for loc in component.in_area(bbox=far, page_size=100) if loc.pk == target.pk] == []
