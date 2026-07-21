"""
Unit tests for SequencesComponent and SequenceRecord schema.

All API calls are mocked — no real server needed.
"""
from __future__ import annotations

from tests.base_component_tests import ComponentUnitTestBase
from trapper_client.components.sequences import SequencesComponent
from trapper_client.schemas import SequenceRecord


# ── datos de prueba ───────────────────────────────────────────────────────────

VALID_RECORD = {
    "pk": 12,
    "sequence_id": 4,
    "sequence_uuid": "6f9619ff-8b86-d011-b42d-00cf4fc964ff",
    "resources": [101, 102, 103],
    "created_at": "2026-04-13T09:30:59+02:00",
}

VALID_RECORD_MINIMAL = {
    "pk": 1,
    "sequence_uuid": "6f9619ff-8b86-d011-b42d-00cf4fc964ff",
    "created_at": "2026-04-13T09:30:59+02:00",
}


def test_endpoint_matches_server_route():
    """El endpoint debe apuntar a media_classification/api/sequences
    (media_classification/urls.py), montado bajo el prefijo
    media_classification/ en la raíz del servidor Trapper."""
    assert SequencesComponent.endpoint == "media_classification/api/sequences"


# ── tests heredados (get / get_all / where / find / export) ──────────────────

class TestSequencesComponent(ComponentUnitTestBase):
    component_class = SequencesComponent
    schema = SequenceRecord
    export_schema = SequenceRecord
    find_pk = 12
    valid_item = VALID_RECORD
    valid_export_item = VALID_RECORD


# ── SequenceRecord ────────────────────────────────────────────────────────────

class TestSequenceRecord:

    def test_parses_full_record(self):
        result = SequenceRecord.model_validate(VALID_RECORD)

        assert result.pk == 12
        assert result.sequence_id == 4
        assert result.resources == [101, 102, 103]

    def test_parses_minimal_record(self):
        """El schema acepta registros sin sequence_id/resources."""
        result = SequenceRecord.model_validate(VALID_RECORD_MINIMAL)

        assert result.pk == 1
        assert result.sequence_id is None
        assert result.resources == []
