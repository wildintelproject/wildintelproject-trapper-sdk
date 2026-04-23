"""
End-to-end tests for ClassificationsComponent against a real Trapper server.

Requires environment variables:
    WILDINTEL_BASE_URL, WILDINTEL_ACCESS_TOKEN, WILDINTEL_SMOKE_ENABLED=1

Optional:
    WILDINTEL_CLASSIFICATION_RESULT_PK     — pk of an existing classification result
    WILDINTEL_CLASSIFICATION_PROJECT_PK    — pk of an existing classification project
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.base_component_tests import ComponentE2ETestBase
from trapper_client.api_query import APIQuery
from trapper_client.components.classifications import ClassificationsComponent
from trapper_client.schemas import ClassificationRecordExport, PaginatedResult


# ── helpers ───────────────────────────────────────────────────────────────────

def _result_pk() -> str:
    return os.getenv("WILDINTEL_CLASSIFICATION_RESULT_PK", "").strip()


def _project_pk() -> str:
    return os.getenv("WILDINTEL_CLASSIFICATION_PROJECT_PK", "").strip()


# ── tests heredados ───────────────────────────────────────────────────────────

class TestClassificationsComponentE2E(ComponentE2ETestBase):
    component_class = ClassificationsComponent
    schema = ClassificationResultRecord
    export_schema = ClassificationResultRecord
    env_pk_var = "WILDINTEL_CLASSIFICATION_RESULT_PK"


# ── tests específicos de project results ─────────────────────────────────────

class TestProjectResultsE2E:

    @pytest.fixture(scope="class")
    def component(self, real_api_base):
        return ClassificationsComponent(real_api_base)

    # ── get_project_results ───────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_get_project_results_returns_paginated_result(self, component):
        """get_project_results() devuelve PaginatedResult."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.get_project_results(int(pk), page_size=5)

        assert isinstance(result, PaginatedResult)
        assert result.pagination.page == 1

    @pytest.mark.e2e
    def test_get_project_results_returns_correct_schema(self, component):
        """get_project_results() devuelve instancias de ClassificationResultRecord."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.get_project_results(int(pk), page_size=5)

        if not result.results:
            pytest.skip("No classification results available for this project")

        assert all(isinstance(row, ClassificationResultRecord) for row in result.results)

    @pytest.mark.e2e
    def test_get_project_results_page_size_respected(self, component):
        """get_project_results() respeta el page_size solicitado."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.get_project_results(int(pk), page_size=3)

        assert len(result.results) <= 3

    @pytest.mark.e2e
    def test_get_project_results_validate_false_returns_models(self, component):
        """get_project_results() con validate=False devuelve modelos sin validar."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.get_project_results(int(pk), page_size=5, validate=False)

        if not result.results:
            pytest.skip("No classification results available for this project")

        assert all(isinstance(row, ClassificationResultRecord) for row in result.results)

    @pytest.mark.e2e
    def test_get_project_results_passes_filter(self, component):
        """get_project_results() pasa filtros al servidor."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        all_results = component.get_project_results(int(pk), page_size=50)
        filtered = component.get_project_results(int(pk), page_size=50, approved=True)

        assert len(filtered.results) <= len(all_results.results)

    # ── where_project_results ─────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_where_project_results_returns_api_query(self, component):
        """where_project_results() devuelve un APIQuery."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        assert isinstance(component.where_project_results(int(pk)), APIQuery)

    @pytest.mark.e2e
    def test_where_project_results_iterates_correct_schema(self, component):
        """Iterar where_project_results() devuelve instancias de ClassificationResultRecord."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        items = []
        for row in component.where_project_results(int(pk), page_size=10):
            items.append(row)
            if len(items) >= 5:
                break

        if not items:
            pytest.skip("No classification results available for this project")

        assert all(isinstance(row, ClassificationResultRecord) for row in items)

    @pytest.mark.e2e
    def test_where_project_results_context_manager_exhausts_on_exit(self, component):
        """where_project_results() como context manager queda exhausto al salir."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        with component.where_project_results(int(pk), page_size=5) as query:
            next(query, None)

        assert query._exhausted is True

    @pytest.mark.e2e
    def test_where_project_results_no_project_pk_in_query_params(self, component):
        """where_project_results() no envía project_pk como query param."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        query = component.where_project_results(int(pk))

        assert "project_pk" not in query.query

    # ── export_project_results ────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_export_project_results_returns_list_when_file_none(self, component):
        """export_project_results() sin file devuelve lista de modelos."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.export_project_results(int(pk), file=None)

        assert isinstance(result, list)
        if result:
            assert isinstance(result[0], ClassificationResultRecord)

    @pytest.mark.e2e
    def test_export_project_results_writes_csv(self, component, tmp_path):
        """export_project_results() escribe CSV y devuelve Path."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        out = tmp_path / "results.csv"
        result = component.export_project_results(int(pk), file=out)

        assert isinstance(result, Path)
        assert out.exists()
        assert out.stat().st_size > 0

    @pytest.mark.e2e
    def test_export_project_results_csv_has_content(self, component, tmp_path):
        """El CSV exportado tiene cabecera y al menos una fila de datos."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        out = tmp_path / "results.csv"
        component.export_project_results(int(pk), file=out)

        lines = out.read_text(encoding="utf-8").strip().splitlines()
        if len(lines) < 2:
            pytest.skip("No classification results available for this project")

        assert len(lines) >= 2

    @pytest.mark.e2e
    def test_export_project_results_validate_false(self, component, tmp_path):
        """export_project_results() con validate=False devuelve Path."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        out = tmp_path / "results_raw.csv"
        result = component.export_project_results(int(pk), file=out, validate=False)

        assert isinstance(result, Path)

    @pytest.mark.e2e
    def test_export_project_results_camtrap_format(self, component, tmp_path):
        """export_project_results() con camtrapdp=True exporta en formato CamTrap."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        out = tmp_path / "results_camtrap.csv"
        result = component.export_project_results(int(pk), file=out, camtrapdp=True)

        assert isinstance(result, Path)
        assert out.exists()

    @pytest.mark.e2e
    def test_export_project_results_with_filter(self, component):
        """export_project_results() con filtro devuelve subconjunto."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        all_results = component.export_project_results(int(pk), file=None)
        filtered = component.export_project_results(int(pk), file=None, approved=True)

        assert len(filtered) <= len(all_results)