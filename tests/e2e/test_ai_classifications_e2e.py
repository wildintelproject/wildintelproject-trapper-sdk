"""
End-to-end tests for AIClassificationsComponent against a real Trapper server.

Requires environment variables:
    WILDINTEL_BASE_URL, WILDINTEL_ACCESS_TOKEN, WILDINTEL_SMOKE_ENABLED=1

Optional:
    WILDINTEL_AI_CLASSIFICATION_PK         — pk of an existing AI classification record
    WILDINTEL_CLASSIFICATION_PROJECT_PK    — pk of an existing classification project (for export)
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.base_component_tests import ComponentE2ETestBase
from trapper_client.api_query import APIQuery
from trapper_client.components.ai_classifications import AIClassificationsComponent
from trapper_client.schemas import (
    AIClassificationRecord,
    AIClassificationRecordExport,
    AIClassificationRecordExportTrapper,
    AIClassificationRecordExportCamTrap,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _ai_pk() -> str:
    return os.getenv("WILDINTEL_AI_CLASSIFICATION_PK", "").strip()


def _project_pk() -> str:
    return os.getenv("WILDINTEL_CLASSIFICATION_PROJECT_PK", "").strip()


# ── tests heredados ───────────────────────────────────────────────────────────

class TestAIClassificationsComponentE2E(ComponentE2ETestBase):
    component_class = AIClassificationsComponent
    schema = AIClassificationRecord
    export_schema = AIClassificationRecordExport
    env_pk_var = "WILDINTEL_AI_CLASSIFICATION_PK"


# ── tests específicos de export ───────────────────────────────────────────────

class TestAIClassificationsExportE2E:

    @pytest.fixture(scope="class")
    def component(self, real_api_base):
        return AIClassificationsComponent(real_api_base)

    @pytest.mark.e2e
    def test_export_returns_list_when_file_none(self, component):
        """export() sin file devuelve lista de modelos de export."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.export(int(pk), file=None)

        assert isinstance(result, list)

    @pytest.mark.e2e
    def test_export_returns_correct_schema_instances(self, component):
        """export() devuelve instancias de Trapper o CamTrap schema según los datos."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.export(int(pk), file=None)

        if not result:
            pytest.skip("No AI classification results available for this project")

        for item in result:
            assert isinstance(item, (AIClassificationRecordExportTrapper, AIClassificationRecordExportCamTrap))

    @pytest.mark.e2e
    def test_export_camtrap_format_returns_camtrap_instances(self, component):
        """export() con camtrapdp=True devuelve instancias CamTrap."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.export(int(pk), file=None, camtrapdp=True)

        if not result:
            pytest.skip("No AI classification results available for this project")

        assert all(isinstance(item, AIClassificationRecordExportCamTrap) for item in result)

    @pytest.mark.e2e
    def test_export_trapper_format_returns_trapper_instances(self, component):
        """export() con camtrapdp=False devuelve instancias Trapper."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.export(int(pk), file=None, camtrapdp=False)

        if not result:
            pytest.skip("No AI classification results available for this project")

        assert all(isinstance(item, AIClassificationRecordExportTrapper) for item in result)

    @pytest.mark.e2e
    def test_export_writes_csv_when_file_provided(self, component, tmp_path):
        """export() escribe CSV y devuelve Path."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        out = tmp_path / "ai_export.csv"
        result = component.export(int(pk), file=out)

        assert isinstance(result, Path)
        assert out.exists()
        assert out.stat().st_size > 0

    @pytest.mark.e2e
    def test_export_csv_has_content(self, component, tmp_path):
        """El CSV exportado tiene cabecera y al menos una fila de datos."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        out = tmp_path / "ai_export.csv"
        component.export(int(pk), file=out)

        lines = out.read_text(encoding="utf-8").strip().splitlines()
        if len(lines) < 2:
            pytest.skip("No AI classification results available for this project")

        assert len(lines) >= 2  # cabecera + al menos una fila

    @pytest.mark.e2e
    def test_export_validate_false_returns_path(self, component, tmp_path):
        """export() con validate=False devuelve Path cuando se proporciona file."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        out = tmp_path / "ai_export_raw.csv"
        result = component.export(int(pk), file=out, validate=False)

        assert isinstance(result, Path)

    @pytest.mark.e2e
    def test_export_with_filter_returns_subset(self, component):
        """export() con filtro devuelve subconjunto de resultados."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        all_results = component.export(int(pk), file=None)
        if not all_results:
            pytest.skip("No AI classification results available for this project")

        filtered_results = component.export(int(pk), file=None, approved=True)

        assert len(filtered_results) <= len(all_results)