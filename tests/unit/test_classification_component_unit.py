"""
Unit tests for ClassificationsComponent.

All API calls are mocked — no real server needed.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import ComponentUnitTestBase, paginated_response
from trapper_client.api_query import APIQuery
from trapper_client.components.classifications import ClassificationsComponent
from trapper_client.schemas import (
    ClassificationRecord,
    ClassificationRecordExport,
    ClassificationResultRecordCamtrapDP,
    ClassificationResultRecordTrapper,
    PaginatedResult,
)


# ── datos de prueba ───────────────────────────────────────────────────────────

VALID_RECORD = {
    "pk": 1,
    "resource": {"pk": 10, "name": "resource.jpg"},
    "collection": 5,
    "updated_at": "2024-01-01T00:00:00Z",
    "is_setup": False,
    "dynamic_attrs": [],
    "status": True,
    "status_ai": False,
    "classified": True,
    "classified_ai": False,
    "classification_project": "/api/projects/7/",
    "detail_data": "/api/classifications/1/",
    "delete_data": "/api/classifications/1/delete/",
    "classify_data": "/api/classifications/1/classify/",
    "update_data": "/api/classifications/1/update/",
    "bboxes": False,
}

VALID_EXPORT_RECORD = {
    "observationID": 1,
    "deploymentID": "deploy_001",
    "mediaID": 10,
    "eventID": "event_001",
    "eventStart": "2024-01-01T08:00:00Z",
    "eventEnd": "2024-01-01T08:01:00Z",
    "observationLevel": "media",
    "observationType": "animal",
}

PROJECT_PK = 7


# ── tests heredados ───────────────────────────────────────────────────────────

class TestClassificationsComponent(ComponentUnitTestBase):
    component_class = ClassificationsComponent
    schema = ClassificationRecord
    export_schema = ClassificationResultRecordCamtrapDP
    find_pk = 1
    valid_item = VALID_RECORD
    valid_export_item = VALID_EXPORT_RECORD


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return MagicMock()


@pytest.fixture
def component(client):
    return ClassificationsComponent(client)


# ── _resolve_export_endpoint ──────────────────────────────────────────────────

class TestResolveExportEndpoint:

    @pytest.fixture
    def component(self):
        return ClassificationsComponent(MagicMock())

    def test_resolves_project_pk_in_endpoint(self, component):
        """_resolve_export_endpoint() sustituye {project_pk} correctamente."""
        result = component._resolve_export_endpoint(PROJECT_PK)
        assert str(PROJECT_PK) in result
        assert "{project_pk}" not in result

    def test_returns_string(self, component):
        """_resolve_export_endpoint() devuelve un string."""
        assert isinstance(component._resolve_export_endpoint(PROJECT_PK), str)

    def test_contains_expected_path(self, component):
        """_resolve_export_endpoint() contiene la ruta base correcta."""
        result = component._resolve_export_endpoint(PROJECT_PK)
        assert "classifications/results" in result


# ── get_project_results ───────────────────────────────────────────────────────

class TestGetProjectResults:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return ClassificationsComponent(client)

    def _expected_endpoint(self, component):
        return component._resolve_export_endpoint(PROJECT_PK)

    def test_returns_paginated_result(self, component, client):
        """get_project_results() devuelve PaginatedResult con items tipados."""
        client.get.return_value = paginated_response([VALID_EXPORT_RECORD])

        result = component.get_project_results(PROJECT_PK)

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], (ClassificationResultRecordCamtrapDP, ClassificationResultRecordTrapper))

    def test_uses_correct_endpoint(self, component, client):
        """get_project_results() usa el export_endpoint con project_pk resuelto."""
        client.get.return_value = paginated_response([])

        component.get_project_results(PROJECT_PK)

        assert client.get.call_args[0][0] == self._expected_endpoint(component)

    def test_sends_page_and_page_size(self, component, client):
        """get_project_results() envía page y page_size al cliente."""
        client.get.return_value = paginated_response([])

        component.get_project_results(PROJECT_PK, page=2, page_size=25)

        params = client.get.call_args[1]["query"]
        assert params["page"] == 2
        assert params["page_size"] == 25

    def test_passes_extra_kwargs(self, component, client):
        """get_project_results() pasa kwargs como parámetros de consulta."""
        client.get.return_value = paginated_response([])

        component.get_project_results(PROJECT_PK, approved=True, species=42)

        params = client.get.call_args[1]["query"]
        assert params["approved"] is True
        assert params["species"] == 42

    def test_validate_false_returns_models(self, component, client):
        """get_project_results() con validate=False construye sin validación."""
        client.get.return_value = paginated_response([VALID_EXPORT_RECORD])

        result = component.get_project_results(PROJECT_PK, validate=False)

        assert isinstance(result.results[0], (ClassificationResultRecordCamtrapDP, ClassificationResultRecordTrapper))

    def test_page_size_respected(self, component, client):
        """get_project_results() envía el page_size correcto."""
        client.get.return_value = paginated_response([])

        component.get_project_results(PROJECT_PK, page_size=3)

        params = client.get.call_args[1]["query"]
        assert params["page_size"] == 3


# ── where_project_results ─────────────────────────────────────────────────────

class TestWhereProjectResults:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return ClassificationsComponent(client)

    def _expected_endpoint(self, component):
        return component._resolve_export_endpoint(PROJECT_PK)

    def test_returns_api_query(self, component):
        """where_project_results() devuelve un APIQuery."""
        assert isinstance(component.where_project_results(PROJECT_PK), APIQuery)

    def test_uses_correct_endpoint(self, component):
        """where_project_results() usa el export_endpoint con project_pk resuelto."""
        query = component.where_project_results(PROJECT_PK)
        assert query.endpoint == self._expected_endpoint(component)

    def test_uses_correct_schema(self, component):
        """where_project_results() usa ClassificationResultRecord como schema."""
        query = component.where_project_results(PROJECT_PK)
        assert query.schema is ClassificationRecordExport

    def test_passes_page_size(self, component):
        """where_project_results() pasa page_size al APIQuery."""
        query = component.where_project_results(PROJECT_PK, page_size=100)
        assert query._page_size == 100

    def test_passes_extra_kwargs(self, component):
        """where_project_results() pasa kwargs como parámetros de consulta."""
        query = component.where_project_results(PROJECT_PK, approved=True, species=42)
        assert query.query["approved"] is True
        assert query.query["species"] == 42

    def test_validate_false(self, component):
        """where_project_results() pasa validate=False al APIQuery."""
        query = component.where_project_results(PROJECT_PK, validate=False)
        assert query.validate is False

    def test_does_not_add_project_pk_to_query_params(self, component):
        """where_project_results() no añade project_pk como query param."""
        query = component.where_project_results(PROJECT_PK)
        assert "project_pk" not in query.query


# ── export_project_results ────────────────────────────────────────────────────

class TestExportProjectResults:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return ClassificationsComponent(client)

    def _expected_endpoint(self, component):
        return component._resolve_export_endpoint(PROJECT_PK)

    def test_returns_list_when_file_none(self, component, client):
        """export_project_results() devuelve lista de modelos cuando file=None."""
        client.get_all.return_value = paginated_response([VALID_EXPORT_RECORD])

        result = component.export_project_results(PROJECT_PK, file=None)

        assert isinstance(result, list)
        assert isinstance(result[0], (ClassificationResultRecordCamtrapDP, ClassificationResultRecordTrapper))

    def test_uses_correct_endpoint(self, component, client):
        """export_project_results() usa el export_endpoint con project_pk resuelto."""
        client.get_all.return_value = paginated_response([])

        component.export_project_results(PROJECT_PK, file=None)

        assert client.get_all.call_args[0][0] == self._expected_endpoint(component)

    def test_writes_csv_when_file_provided(self, component, client, tmp_path):
        """export_project_results() escribe CSV y devuelve Path cuando se indica file."""
        client.get_all.return_value = paginated_response([VALID_EXPORT_RECORD])
        out = tmp_path / "results.csv"
        client._select_file.return_value = out
        client._write_csv = MagicMock()

        result = component.export_project_results(PROJECT_PK, file=out)

        assert isinstance(result, Path)
        client._write_csv.assert_called_once()

    def test_validate_false_uses_get_all(self, component, client):
        """export_project_results() con validate=False sigue usando get_all."""
        client.get_all.return_value = paginated_response([VALID_EXPORT_RECORD])

        component.export_project_results(PROJECT_PK, file=None, validate=False)

        client.get_all.assert_called_once()

    def test_passes_extra_kwargs(self, component, client):
        """export_project_results() pasa kwargs como parámetros de consulta."""
        client.get_all.return_value = paginated_response([])

        component.export_project_results(PROJECT_PK, file=None, approved=True)

        params = client.get_all.call_args[1]["query"]
        assert params["approved"] is True

    def test_returns_empty_list_when_no_results(self, component, client):
        """export_project_results() devuelve lista vacía si no hay resultados."""
        client.get_all.return_value = paginated_response([])

        result = component.export_project_results(PROJECT_PK, file=None)

        assert result == []