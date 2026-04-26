"""
End-to-end tests for ClassificationsMapComponent against a real Trapper server.

Requires environment variables:
    WILDINTEL_BASE_URL, WILDINTEL_ACCESS_TOKEN, WILDINTEL_SMOKE_ENABLED=1

Optional:
    WILDINTEL_CLASSIFICATIONS_MAP_PK  — pk of an existing classifications map record
"""
from __future__ import annotations

from tests.base_component_tests import ComponentE2ETestBase
from trapper_client.components.classifications_map import ClassificationsMapComponent
from trapper_client.schemas import ClassificationMapRecord


class TestClassificationsMapComponentE2E(ComponentE2ETestBase):
    component_class = ClassificationsMapComponent
    schema = ClassificationMapRecord
    export_schema = ClassificationMapRecord
    env_pk_var = "WILDINTEL_CLASSIFICATIONS_MAP_PK"
