"""
End-to-end tests for LocationsComponent.

Requires environment variables:
    WILDINTEL_BASE_URL, WILDINTEL_ACCESS_TOKEN, WILDINTEL_SMOKE_ENABLED=1

Optional:
    WILDINTEL_LOCATION_PK — pk of an existing location (for find tests)
"""
from tests.base_component_tests import ComponentE2ETestBase
from trapper_client.components.locations import LocationsComponent
from trapper_client.schemas import Location, LocationExport


class TestLocationsComponentE2E(ComponentE2ETestBase):
    component_class = LocationsComponent
    schema = Location
    export_schema = LocationExport
    env_pk_var = "WILDINTEL_LOCATION_PK"