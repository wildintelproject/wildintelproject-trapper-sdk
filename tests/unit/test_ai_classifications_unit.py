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

VALID_RECORD = {
      "pk": 1,
      "owner": "Pedro Garcia",
      "owner_profile": "/accounts/profile/pedro.garcia@dci.uhu.es/",
      "classification": 480196,
      "resource": {
        "pk": 2379965,
        "name": "R9999-DONA_9999__20041124_1.JPEG",
        "resource_type": "I",
        "thumbnail_url": "/storage/resource/media/2379965/tfile/",
        "url": "/storage/resource/media/2379965/pfile/",
        "mime": "image/jpeg",
        "date_recorded": "2004-11-24T07:22:00+01:00",
        "deployment": 658,
        "deployment_id": "r9999-dona_9999"
      },
      "collection": 36,
      "updated_at": "2025-10-01T13:51:16.385117+02:00",
      "approved": False,
      "created_at": "2025-10-01T13:51:16.385116+02:00",
      "static_attrs": {},
      "dynamic_attrs": [
        {
          "observation_type": "animal",
          "species": "None",
          "count": "1",
          "classification_confidence": "0.94"
        }
      ],
      "detail_data": "/media_classification/classify/480196/ai/17/",
      "delete_data": "/media_classification/ai_classifications/delete/10659/",
      "ai_provider": "Yolo Donana 20250909"
    }

VALID_EXPORT_TRAPPER = {
    "observationID": 1319,
    "deploymentID": "r0001-wicp_0001",
    "mediaID": "3758932",
    "eventID": "75ca0927-e4b1-401f-950c-2d7978ad1d86",
    "eventStart": "2023-03-13T13:58:10+0000",
    "eventEnd": "2023-03-13T13:58:10+0000",
    "observationLevel": "media",
    "observationType": "animal",
    "cameraSetupType": None,
    "scientificName": "Canis familiaris",
    "count": 1,
    "lifeStage": None,
    "sex": None,
    "behavior": None,
    "individualID": None,
    "individualPositionRadius": None,
    "individualPositionAngle": None,
    "individualSpeed": None,
    "bboxX": None,
    "bboxY": None,
    "bboxWidth": None,
    "bboxHeight": None,
    "classificationMethod": None,
    "classifiedBy": "DeepFaune Classifier v1.3 (34 species)",
    "classificationTimestamp": "2026-02-17 22:30:22.299869+00:00",
    "classificationProbability": 0.69,
    "observationTags": None,
    "observationComments": None,
    "countNew": None,
    "englishName": "Domestic dog",
    "bboxes": [[0.18875, 0.11851851851851852, 0.17500000000000002, 0.74]],
    "_id": 89749
}

VALID_EXPORT_CAMTRAP = {
    "observationID": None,
    "deploymentID": "r0001-wicp_0001",
    "mediaID": "3758932",
    "eventID": "75ca0927-e4b1-401f-950c-2d7978ad1d86",
    "eventStart": "2023-03-13T13:58:10+0000",
    "eventEnd": "2023-03-13T13:58:10+0000",
    "observationLevel": "media",
    "observationType": "human",
    "cameraSetupType": None,
    "scientificName": "Homo sapiens",
    "count": 1,
    "lifeStage": None,
    "sex": None,
    "behavior": None,
    "individualID": None,
    "individualPositionRadius": None,
    "individualPositionAngle": None,
    "individualSpeed": None,
    "bboxX": 0.45425501465797424,
    "bboxY": 0.27042025327682495,
    "bboxWidth": 0.2161982953548431,
    "bboxHeight": 0.5533119440078735,
    "classificationMethod": None,
    "classifiedBy": "MegaDetector V6 v10n",
    "classificationTimestamp": "2025-12-16 16:24:21.684878+00:00",
    "classificationProbability": 0.89,
    "observationTags": None,
    "observationComments": None
}

PROJECT_PK = 7


# ── tests heredados ───────────────────────────────────────────────────────────

class TestAIClassificationsComponent(ComponentUnitTestBase):
    component_class = AIClassificationsComponent
    schema = AIClassificationRecord
    export_schema = AIClassificationRecordExportTrapper
    find_pk = 1
    valid_item = VALID_RECORD
    valid_export_item = VALID_EXPORT_TRAPPER

    # excluir tests de export heredados porque la firma es diferente
    test_export_returns_list_when_file_is_none = None
    test_export_uses_export_schema_by_default = None
    test_export_uses_export_endpoint_by_default = None
    test_export_uses_overwrite_endpoint = None
    test_export_uses_overwrite_schema = None
    test_export_writes_csv_when_file_provided = None
    test_export_validate_false_constructs_without_validation = None


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
        mock_record = MagicMock(spec=AIClassificationRecordExportTrapper)
        component._validate_ai_export_record = MagicMock(return_value=mock_record)
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

    def test_export_writes_csv_when_file_provided(self, component, client, tmp_path):
        """export() escribe CSV y devuelve Path cuando se indica file."""
        mock_record = MagicMock(spec=AIClassificationRecordExportTrapper)
        component._validate_ai_export_record = MagicMock(return_value=mock_record)
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