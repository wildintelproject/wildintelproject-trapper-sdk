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
    AIClassification,
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
    schema = AIClassification
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
    # export(raw=True) is not on this component: its own export() saves the raw CSV with validate=False
    test_export_raw_saves_the_csv_as_the_server_sends_it = None
    test_export_raw_needs_a_file = None
    test_export_is_not_raw_by_default = None


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return MagicMock()


@pytest.fixture
def component(client):
    return AIClassificationsComponent(client)


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

    def test_export_accepts_empty_strings_in_rows(self, component, client):
        """export() reads the empty cells of the CSV (an empty eventID, with no sequences, stays valid)."""
        dirty_row = {**VALID_EXPORT_TRAPPER, "some_field": "", "eventID": "", "lifeStage": ""}
        client.get_all.return_value = paginated_response([dirty_row])

        result = component.export(PROJECT_PK, file=None)

        assert isinstance(result[0], AIClassificationRecordExportTrapper)


# ── regresión: classificationTimestamp="" (mismo bug que en classifications) ─

class TestAIClassificationTimestampEmptyString:

    def test_trapper_flavor_accepts_empty_classification_timestamp(self):
        """AIClassificationRecordExportTrapper acepta classificationTimestamp=''."""
        row = {**VALID_EXPORT_TRAPPER, "classificationTimestamp": ""}
        result = AIClassificationRecordExportTrapper.model_validate(row)
        assert result.classificationTimestamp is None

    def test_camtrap_flavor_accepts_empty_classification_timestamp(self):
        """AIClassificationRecordExportCamTrap acepta classificationTimestamp=''."""
        row = {**VALID_EXPORT_CAMTRAP, "classificationTimestamp": ""}
        result = AIClassificationRecordExportCamTrap.model_validate(row)
        assert result.classificationTimestamp is None

# ── the rows of Trapper v1 and v2 (captured from the test servers) ────────────

# v1, camtrapdp=True: observationID and eventID empty (no sequences)
V1_CAMTRAP_ROW = {
    "observationID": "", "deploymentID": "don01-2024a", "mediaID": "5", "eventID": "",
    "eventStart": "2024-03-19T13:30:31+0100", "eventEnd": "2024-03-19T13:30:31+0100",
    "observationLevel": "media", "observationType": "animal", "cameraSetupType": "",
    "scientificName": "Oryctolagus cuniculus", "count": "1", "lifeStage": "", "sex": "", "behavior": "",
    "individualID": "", "individualPositionRadius": "", "individualPositionAngle": "", "individualSpeed": "",
    "bboxX": "0.1", "bboxY": "0.1", "bboxWidth": "0.3", "bboxHeight": "0.3", "classificationMethod": "",
    "classifiedBy": "SDK test provider", "classificationTimestamp": "2026-11-24 11:38:51.050903+00:00",
    "classificationProbability": "0.93", "observationTags": "", "observationComments": "",
}

# v2, camtrapdp=False: one flat box
V2_TRAPPER_ROW = {
    **{k: v for k, v in V1_CAMTRAP_ROW.items() if not k.startswith("bbox")},
    "observationID": "1", "bboxX": "", "bboxY": "", "bboxWidth": "", "bboxHeight": "",
    "classifiedBy": "DeepFaune Classifier v1.2", "classificationTimestamp": "",
    "countNew": "", "englishName": "European Rabbit", "bboxes": "[0.1,0.1,0.3,0.3]", "_id": "88",
}


class TestExportRowsOfBothVersions:

    def test_v1_camtrapdp_row_with_empty_event_and_observation(self, component, client):
        client.get_all.return_value = paginated_response([V1_CAMTRAP_ROW])
        row = component.export(PROJECT_PK)[0]
        assert isinstance(row, AIClassificationRecordExportCamTrap)
        assert row.observationID is None and row.eventID == ""
        assert row.bboxX == 0.1 and row.classificationProbability == 0.93

    def test_v2_trapper_row_with_a_flat_box(self, component, client):
        client.get_all.return_value = paginated_response([V2_TRAPPER_ROW])
        row = component.export(PROJECT_PK, camtrapdp=False)[0]
        assert isinstance(row, AIClassificationRecordExportTrapper)
        assert row.id == 88 and len(row.bboxes) == 1 and row.bboxes[0].width == 0.3
        assert row.classificationTimestamp is None

    def test_the_ai_rows_are_results_table_rows(self):
        from trapper_client.schemas import ClassificationResultRecordCamtrapDP, ClassificationResultRecordTrapper

        assert issubclass(AIClassificationRecordExportCamTrap, ClassificationResultRecordCamtrapDP)
        assert issubclass(AIClassificationRecordExportTrapper, ClassificationResultRecordTrapper)


class TestExportWithNoRows:
    """Trapper answers ``400 "Empty queryset ..."`` for a project with no AI classifications."""

    @staticmethod
    def _empty():
        from trapper_client import err

        return err.BadRequestError(
            '["Empty queryset or you have no permission to access the requested objects."]',
        )

    def test_list_is_empty(self, component, client):
        client.get_all.side_effect = self._empty()
        assert component.export(PROJECT_PK) == []

    def test_file_is_empty(self, component, client, tmp_path):
        client.get_all.side_effect = self._empty()
        out = tmp_path / "ai.csv"
        client._select_file.return_value = out
        client._write_csv = lambda rows, path: path.write_text("")
        assert component.export(PROJECT_PK, file=out) == out and out.read_text() == ""

    def test_validate_false_file_is_empty(self, component, client, tmp_path):
        client.export_all.side_effect = self._empty()
        out = tmp_path / "ai.csv"
        client._select_file.return_value = out
        assert component.export(PROJECT_PK, file=out, validate=False) == out and out.read_text() == ""

    def test_other_400s_still_raise(self, component, client):
        from trapper_client import err

        client.get_all.side_effect = err.BadRequestError("{'species': ['Select a valid choice.']}")
        with pytest.raises(err.BadRequestError):
            component.export(PROJECT_PK)


class TestCamtrapdpParam:
    """Trapper compares ``camtrapdp`` with the text ``"True"``: a Python ``True`` went out as ``true`` = False."""

    @pytest.mark.parametrize("value, sent", [(True, "True"), (False, "False"), ("true", "True"), ("FALSE", "False")])
    def test_export_sends_camtrapdp_as_trapper_reads_it(self, component, client, value, sent):
        client.get_all.return_value = paginated_response([])
        component.export(PROJECT_PK, camtrapdp=value)
        assert client.get_all.call_args[1]["query"]["camtrapdp"] == sent

    def test_anything_else_is_a_value_error(self, component, client):
        with pytest.raises(ValueError, match="camtrapdp must be True or False"):
            component.export(PROJECT_PK, camtrapdp="yes")

    def test_not_sent_when_not_given(self, component, client):
        client.get_all.return_value = paginated_response([])
        component.export(PROJECT_PK)
        assert "camtrapdp" not in client.get_all.call_args[1]["query"]

    @pytest.mark.parametrize("value, sent", [(True, "True"), (False, "False")])
    def test_results_table_of_classification_results_too(self, value, sent):
        from trapper_client.components.classifications import ClassificationsComponent

        client = MagicMock()
        client.server_version = "v2"
        client.get.return_value = paginated_response([])
        ClassificationsComponent(client).get_project_results(PROJECT_PK, camtrapdp=value)
        assert client.get.call_args[1]["query"]["camtrapdp"] == sent
