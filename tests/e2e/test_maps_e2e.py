"""
End-to-end tests for MapsComponent against a real Trapper server.

Requires environment variables:
    WILDINTEL_BASE_URL, WILDINTEL_ACCESS_TOKEN, WILDINTEL_SMOKE_ENABLED=1

Optional:
    WILDINTEL_MAP_PK  — pk of an existing map record
"""
from __future__ import annotations

from tests.base_component_tests import ComponentE2ETestBase
from trapper_client.components.maps import MapsComponent
from trapper_client.schemas import MapRecord


class TestMapsComponentE2E(ComponentE2ETestBase):
    component_class = MapsComponent
    schema = MapRecord
    export_schema = MapRecord
    env_pk_var = "WILDINTEL_MAP_PK"
