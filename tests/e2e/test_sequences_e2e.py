"""
End-to-end tests for SequencesComponent against a real Trapper server.

Requires environment variables:
    WILDINTEL_BASE_URL, WILDINTEL_ACCESS_TOKEN, WILDINTEL_SMOKE_ENABLED=1

Optional:
    WILDINTEL_SEQUENCE_PK  — pk of an existing sequence record
"""
from __future__ import annotations

from tests.base_component_tests import ComponentE2ETestBase
from trapper_client.components.sequences import SequencesComponent
from trapper_client.schemas import SequenceRecord


class TestSequencesComponentE2E(ComponentE2ETestBase):
    component_class = SequencesComponent
    schema = SequenceRecord
    export_schema = SequenceRecord
    env_pk_var = "WILDINTEL_SEQUENCE_PK"
