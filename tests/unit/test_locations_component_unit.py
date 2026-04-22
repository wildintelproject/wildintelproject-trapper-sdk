"""
Unit tests for LocationsComponent.
"""
from tests.base_component_tests import ComponentUnitTestBase
from trapper_client.components.locations import LocationsComponent
from trapper_client.schemas import Location, LocationExport

class TestLocationsComponent(ComponentUnitTestBase):
    component_class = LocationsComponent
    schema = Location
    export_schema = LocationExport
    find_pk = 1
    valid_item = {"pk": 1, "name": "Location A"}
    valid_export_item = {
        "_id": 1,
        "locationID": "dona_001",
        "latitude": 37.1,
        "longitude": -6.9,
    }