"""
End-to-end tests for ClassificatorsComponent against a real Trapper server.

Requires environment variables:
    WILDINTEL_BASE_URL, WILDINTEL_ACCESS_TOKEN, WILDINTEL_SMOKE_ENABLED=1

Optional:
    WILDINTEL_CLASSIFICATOR_PK  — pk of an existing classificator record
"""
from __future__ import annotations

from tests.base_component_tests import ComponentE2ETestBase
from trapper_client.components.classificators import ClassificatorsComponent
from trapper_client.schemas import ClassificatorRecord


class TestClassificatorsComponentE2E(ComponentE2ETestBase):
    component_class = ClassificatorsComponent
    schema = ClassificatorRecord
    export_schema = ClassificatorRecord
    env_pk_var = "WILDINTEL_CLASSIFICATOR_PK"
