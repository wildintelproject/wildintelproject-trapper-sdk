"""
End-to-end tests for SpeciesComponent against a real Trapper server.

Requires environment variables:
    WILDINTEL_BASE_URL, WILDINTEL_ACCESS_TOKEN, WILDINTEL_SMOKE_ENABLED=1

Optional:
    WILDINTEL_SPECIES_PK  — pk of an existing species record
"""
from __future__ import annotations

from tests.base_component_tests import ComponentE2ETestBase
from trapper_client.components.species import SpeciesComponent
from trapper_client.schemas import SpeciesRecord


class TestSpeciesComponentE2E(ComponentE2ETestBase):
    component_class = SpeciesComponent
    schema = SpeciesRecord
    export_schema = SpeciesRecord
    env_pk_var = "WILDINTEL_SPECIES_PK"
