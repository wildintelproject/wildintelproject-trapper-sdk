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
