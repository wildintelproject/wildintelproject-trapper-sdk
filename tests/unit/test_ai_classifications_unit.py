"""
Unit tests for AIClassificationsComponent.

All API calls are mocked — no real server needed.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import ComponentUnitTestBase, paginated_response
from trapper_client.components.ai_classifications import AIClassificationsComponent
from trapper_client.schemas import (
    AIClassificationRecord,
    AIClassificationRecordExport,
    AIClassificationRecordExportTrapper,
    AIClassificationRecordExportCamTrap,
)


# ── datos de prueba ───────────────────────────────────────────────────────────

VALID_RECORD = {"pk": 1, "name": "AI Classification A"}

VALID_EXPORT_TRAPPER = {
    "_id": 1,
    "locationID": "dona_001",
    "latitude": 37.1,
    "longitude": -6.9,
}

VALID_EXPORT_CAMTRAP = {
    "deploymentID": "deploy_001",
    "mediaID": "media_001",
    "timestamp": "2024-01-01T00:00:00Z",
}

PROJECT_PK = 7


# ── tests heredados ───────────────────────────────────────────────────────────

class TestAIClassificationsComponent(ComponentUnitTestBase):
    component_class = AIClassificationsComponent
    schema = AIClassificationRecord
    export_schema = AIClassificationRecordExport
    find_pk = 1
    valid_item = VALID_RECORD
    valid_export_item = VALID_EXPORT_TRAPPER


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return MagicMock()


@pytest.fixture
def component(client):
    return AIClassificationsComponent(client)


# ── _clean_row ────────────────────────────────────────────────────────────────

class TestCleanRow:

    @pytest.fixture
    def component(self):
        return AIClassificationsComponent(MagicMock())

    def test_replaces_empty_strings_with_none(self, component):
        """_clean_row() reemplaza strings vacíos por None."""
        result = component._clean_row({"name": "test", "value": ""})
        assert result["value"] is None
        assert result["name"] == "test"

    def test_keeps_none_values(self, component):
        """_clean_row() mantiene None existentes."""
        result = component._clean_row({"value": None})
        assert result["value"] is None

    def test_keeps_zero_values(self, component):
        """_clean_row() mantiene valores 0 (no los convierte a None)."""
        result = component._clean_row({"value": 0})
        assert result["value"] == 0

    def test_keeps_false_values(self, component):
        """_clean_row() mantiene False (no lo convierte a None)."""
        result = component._clean_row({"active": False})
        assert result["active"] is False

    def test_handles_empty_dict(self, component):
        """_clean_row() maneja dict vacío."""
        assert component._clean_row({}) == {}

    def test_replaces_multiple_empty_strings(self, component):
        """_clean_row() reemplaza múltiples strings vacíos."""
        result = component._clean_row({"a": "", "b": "", "c": "value"})
        assert result["a"] is None
        assert result["b"] is None
        assert result["c"] == "value"


# ── _validate_ai_export_record ────────────────────────────────────────────────

class TestValidateAIExportRecord:

    @pytest.fixture
    def component(self):
        return AIClassificationsComponent(MagicMock())

    def test_returns_trapper_schema_when_id_field_present(self, component):
        """_validate_ai_export_record() devuelve Trapper schema cuando hay _id."""
        result = component._validate_ai_export_record(VALID_EXPORT_TRAPPER)
        assert isinstance(result, AIClassificationRecordExportTrapper)

    def test_returns_camtrap_schema_when_no_id_field(self, component):
        """_validate_ai_export_record() devuelve CamTrap schema cuando no hay _id."""
        result = component._validate_ai_export_record(VALID_EXPORT_CAMTRAP)
        assert isinstance(result, AIClassificationRecordExportCamTrap)

    def test_cleans_empty_strings_before_validating(self, component):
        """_validate_ai_export_record() limpia strings vacíos antes de validar."""
        row = {**VALID_EXPORT_TRAPPER, "extra_field": ""}
        result = component._validate_ai_export_record(row)
        assert isinstance(result, AIClassificationRecordExportTrapper)


# ── export ────────────────────────────────────────────────────────────────────

class TestExport:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return AIClassificationsComponent(client)

    def _expected_endpoint(self, component):
        return component.export_endpoint.format(project_pk=PROJECT_PK)

    def test_export_uses_correct_endpoint(self, component, client):
        """export() usa el export_endpoint con project_pk resuelto."""
        client.get_all.return_value = paginated_response([])

        component.export(PROJECT_PK, file=None)

        assert client.get_all.call_args[0][0] == self._expected_endpoint(component)

    def test_export_returns_list_of_trapper_models_when_file_none(self, component, client):
        """export() devuelve lista de AIClassificationRecordExportTrapper cuando file=None."""
        client.get_all.return_value = paginated_response([VALID_EXPORT_TRAPPER])

        result = component.export(PROJECT_PK, file=None)

        assert isinstance(result, list)
        assert isinstance(result[0], AIClassificationRecordExportTrapper)

    def test_export_returns_list_of_camtrap_models_when_file_none(self, component, client):
        """export() devuelve lista de AIClassificationRecordExportCamTrap cuando no hay _id."""
        client.get_all.return_value = paginated_response([VALID_EXPORT_CAMTRAP])

        result = component.export(PROJECT_PK, file=None)

        assert isinstance(result, list)
        assert isinstance(result[0], AIClassificationRecordExportCamTrap)

    def test_export_handles_mixed_schema_rows(self, component, client):
        """export() maneja filas con distintos schemas en la misma respuesta."""
        client.get_all.return_value = paginated_response([
            VALID_EXPORT_TRAPPER,
            VALID_EXPORT_CAMTRAP,
        ])

        result = component.export(PROJECT_PK, file=None)

        assert len(result) == 2
        assert isinstance(result[0], AIClassificationRecordExportTrapper)
        assert isinstance(result[1], AIClassificationRecordExportCamTrap)

    def test_export_writes_csv_when_file_provided(self, component, client, tmp_path):
        """export() escribe CSV y devuelve Path cuando se indica file."""
        client.get_all.return_value = paginated_response([VALID_EXPORT_TRAPPER])
        out = tmp_path / "ai_export.csv"
        client._select_file.return_value = out
        client._write_csv = MagicMock()

        result = component.export(PROJECT_PK, file=out)

        assert isinstance(result, Path)
        client._write_csv.assert_called_once()

    def test_export_validate_false_delegates_to_export_all(self, component, client):
        """export() con validate=False delega en client.export_all."""
        client.export_all.return_value = []

        component.export(PROJECT_PK, file=None, validate=False)

        client.export_all.assert_called_once()
        client.get_all.assert_not_called()

    def test_export_passes_query_params(self, component, client):
        """export() pasa query params al cliente."""
        client.get_all.return_value = paginated_response([])

        component.export(PROJECT_PK, file=None, species=42)

        params = client.get_all.call_args[1]["query"]
        assert params["species"] == 42

    def test_export_cleans_empty_strings_in_rows(self, component, client):
        """export() limpia strings vacíos de cada fila antes de parsear."""
        dirty_row = {**VALID_EXPORT_TRAPPER, "some_field": ""}
        client.get_all.return_value = paginated_response([dirty_row])

        result = component.export(PROJECT_PK, file=None)

        assert isinstance(result[0], AIClassificationRecordExportTrapper)