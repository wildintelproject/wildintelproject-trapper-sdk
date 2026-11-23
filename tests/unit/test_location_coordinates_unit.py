"""``Location.longitude`` / ``Location.latitude``: the coordinates Trapper gives as one string."""
from __future__ import annotations

import pytest

from trapper_client import Location
from trapper_client.schemas.locations import parse_lon_lat


class TestParseLonLat:

    @pytest.mark.parametrize("value, expected", [
        ("-6.44, 37.05", (-6.44, 37.05)),            # what Trapper v1 and v2 return: longitude first
        ("-6.44,37.05", (-6.44, 37.05)),
        ("  -6.44 ,  37.05  ", (-6.44, 37.05)),
        ("-6.44 37.05", (-6.44, 37.05)),
        ("0, 0", (0.0, 0.0)),
        ("+10.5, -20", (10.5, -20.0)),
        ("1e1, 2", (10.0, 2.0)),
        ("POINT (-6.44 37.05)", (-6.44, 37.05)),
        ("point(-6.44 37.05)", (-6.44, 37.05)),
        ("SRID=4326;POINT (-6.44 37.05)", (-6.44, 37.05)),
        ("180, 90", (180.0, 90.0)),
        ("-180, -90", (-180.0, -90.0)),
    ])
    def test_readable_forms(self, value, expected):
        assert parse_lon_lat(value) == expected

    @pytest.mark.parametrize("value", [
        None, "", "   ", "abc", "1", "1, 2, 3", "1; 2", "lon, lat", "POINT EMPTY", "POINT (1)",
        "200, 10",       # longitude out of range
        "10, 95",        # latitude out of range
        "-180.5, 0",
        123, 4.5, ["-6.44", "37.05"], {"coordinates": [1, 2]},
    ])
    def test_unreadable_or_out_of_range_is_none_never_an_error(self, value):
        assert parse_lon_lat(value) is None


class TestLocationAttributes:

    def test_longitude_and_latitude_come_from_the_coordinates(self):
        loc = Location(pk=16, coordinates="-6.44, 37.05")
        assert (loc.longitude, loc.latitude) == (-6.44, 37.05)

    def test_the_raw_string_is_untouched(self):
        assert Location(pk=1, coordinates="-6.44, 37.05").coordinates == "-6.44, 37.05"

    @pytest.mark.parametrize("coordinates", [None, "", "garbage", "500, 500"])
    def test_none_when_they_cannot_be_read(self, coordinates):
        loc = Location(pk=1, coordinates=coordinates)
        assert loc.longitude is None and loc.latitude is None

    def test_a_location_without_coordinates(self):
        loc = Location(pk=1)
        assert loc.longitude is None and loc.latitude is None

    def test_they_are_not_fields_of_the_model(self):
        loc = Location(pk=1, coordinates="-6.44, 37.05")
        dumped = loc.model_dump()
        assert "longitude" not in dumped and "latitude" not in dumped
        assert "longitude" not in Location.model_fields

    def test_a_payload_that_sends_those_keys_does_not_shadow_the_parsed_values(self):
        # TrapperSchema allows extra fields: a server that one day sends them must not break the properties
        loc = Location.model_validate(
            {"pk": 1, "coordinates": "-6.44, 37.05", "longitude": 99, "latitude": 99}
        )
        assert (loc.longitude, loc.latitude) == (-6.44, 37.05)
