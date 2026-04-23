"""
End-to-end tests for ClassificationMediaComponent against a real Trapper server.

Requires environment variables:
    WILDINTEL_BASE_URL, WILDINTEL_ACCESS_TOKEN, WILDINTEL_SMOKE_ENABLED=1

Optional:
    WILDINTEL_CLASSIFICATION_PROJECT_PK    — pk of an existing classification project
    WILDINTEL_CLASSIFICATION_COLLECTION_PK — storage collection pk linked to the project
    WILDINTEL_MEDIA_ID                     — pk of an existing media record
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from trapper_client.api_query import APIQuery
from trapper_client.components.classification_media import ClassificationMediaComponent
from trapper_client.schemas import MediaRecord, PaginatedResult


# ── helpers ───────────────────────────────────────────────────────────────────

def _project_pk() -> str:
    return os.getenv("WILDINTEL_CLASSIFICATION_PROJECT_PK", "").strip()


def _collection_pk() -> str:
    return os.getenv("WILDINTEL_CLASSIFICATION_COLLECTION_PK", "").strip()


def _media_id() -> str:
    return os.getenv("WILDINTEL_MEDIA_ID", "").strip()


# ── fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="class")
def component(real_api_base):
    return ClassificationMediaComponent(real_api_base)


# ── project media ─────────────────────────────────────────────────────────────

class TestProjectMediaE2E:

    @pytest.fixture(scope="class")
    def component(self, real_api_base):
        return ClassificationMediaComponent(real_api_base)

    @pytest.mark.e2e
    def test_get_project_media_returns_paginated_result(self, component):
        """get_project_media() devuelve PaginatedResult."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.get_project_media(int(pk), page_size=5)

        assert isinstance(result, PaginatedResult)
        assert result.pagination.page == 1

    @pytest.mark.e2e
    def test_get_project_media_returns_media_record_instances(self, component):
        """get_project_media() devuelve instancias de MediaRecord."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.get_project_media(int(pk), page_size=5)

        if not result.results:
            pytest.skip("No media available for this project")

        assert all(isinstance(row, MediaRecord) for row in result.results)

    @pytest.mark.e2e
    def test_get_project_media_page_size_respected(self, component):
        """get_project_media() respeta el page_size solicitado."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.get_project_media(int(pk), page_size=3)
        assert len(result.results) <= 3

    @pytest.mark.e2e
    def test_get_project_media_validate_false_returns_models(self, component):
        """get_project_media() con validate=False devuelve modelos sin validar."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.get_project_media(int(pk), page_size=5, validate=False)

        if not result.results:
            pytest.skip("No media available for this project")

        assert all(isinstance(row, MediaRecord) for row in result.results)

    @pytest.mark.e2e
    def test_where_project_media_returns_api_query(self, component):
        """where_project_media() devuelve un APIQuery."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        assert isinstance(component.where_project_media(int(pk)), APIQuery)

    @pytest.mark.e2e
    def test_where_project_media_iterates_media_records(self, component):
        """Iterar where_project_media() devuelve instancias de MediaRecord."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        items = []
        for row in component.where_project_media(int(pk), page_size=10):
            items.append(row)
            if len(items) >= 5:
                break

        if not items:
            pytest.skip("No media available for this project")

        assert all(isinstance(row, MediaRecord) for row in items)

    @pytest.mark.e2e
    def test_where_project_media_context_manager_exhausts_on_exit(self, component):
        """where_project_media() como context manager queda exhausto al salir."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        with component.where_project_media(int(pk), page_size=5) as query:
            next(query, None)

        assert query._exhausted is True

    @pytest.mark.e2e
    def test_export_project_media_returns_list_when_file_none(self, component):
        """export_project_media() sin file devuelve lista de MediaRecord."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.export_project_media(int(pk), file=None)

        assert isinstance(result, list)
        if result:
            assert isinstance(result[0], MediaRecord)

    @pytest.mark.e2e
    def test_export_project_media_writes_csv(self, component, tmp_path):
        """export_project_media() escribe CSV y devuelve Path."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        out = tmp_path / "media.csv"
        result = component.export_project_media(int(pk), file=out)

        assert isinstance(result, Path)
        assert out.exists()
        assert out.stat().st_size > 0

    @pytest.mark.e2e
    def test_get_project_media_by_id_returns_record_when_found(self, component):
        """get_project_media_by_id() devuelve MediaRecord cuando el id existe."""
        pk = _project_pk()
        media_id = _media_id()
        if not pk or not media_id:
            pytest.skip(
                "Set WILDINTEL_CLASSIFICATION_PROJECT_PK and "
                "WILDINTEL_MEDIA_ID to run this test"
            )

        result = component.get_project_media_by_id(int(pk), int(media_id))

        assert result is not None
        assert isinstance(result, MediaRecord)

    @pytest.mark.e2e
    def test_get_project_media_by_id_returns_none_when_not_found(self, component):
        """get_project_media_by_id() devuelve None para un media_id inexistente."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.get_project_media_by_id(int(pk), media_id=999999999)

        assert result is None


# ── collection media ──────────────────────────────────────────────────────────

class TestCollectionMediaE2E:

    @pytest.fixture(scope="class")
    def component(self, real_api_base):
        return ClassificationMediaComponent(real_api_base)

    @pytest.mark.e2e
    def test_get_collection_media_returns_paginated_result(self, component):
        """get_collection_media() devuelve PaginatedResult."""
        pk = _project_pk()
        col_pk = _collection_pk()
        if not pk or not col_pk:
            pytest.skip(
                "Set WILDINTEL_CLASSIFICATION_PROJECT_PK and "
                "WILDINTEL_CLASSIFICATION_COLLECTION_PK to run this test"
            )

        result = component.get_collection_media(int(pk), int(col_pk), page_size=5)

        assert isinstance(result, PaginatedResult)

    @pytest.mark.e2e
    def test_get_collection_media_returns_media_record_instances(self, component):
        """get_collection_media() devuelve instancias de MediaRecord."""
        pk = _project_pk()
        col_pk = _collection_pk()
        if not pk or not col_pk:
            pytest.skip(
                "Set WILDINTEL_CLASSIFICATION_PROJECT_PK and "
                "WILDINTEL_CLASSIFICATION_COLLECTION_PK to run this test"
            )

        result = component.get_collection_media(int(pk), int(col_pk), page_size=5)

        if not result.results:
            pytest.skip("No media available for this collection")

        assert all(isinstance(row, MediaRecord) for row in result.results)

    @pytest.mark.e2e
    def test_where_collection_media_returns_api_query(self, component):
        """where_collection_media() devuelve un APIQuery."""
        pk = _project_pk()
        col_pk = _collection_pk()
        if not pk or not col_pk:
            pytest.skip(
                "Set WILDINTEL_CLASSIFICATION_PROJECT_PK and "
                "WILDINTEL_CLASSIFICATION_COLLECTION_PK to run this test"
            )

        assert isinstance(component.where_collection_media(int(pk), int(col_pk)), APIQuery)

    @pytest.mark.e2e
    def test_where_collection_media_iterates_media_records(self, component):
        """Iterar where_collection_media() devuelve instancias de MediaRecord."""
        pk = _project_pk()
        col_pk = _collection_pk()
        if not pk or not col_pk:
            pytest.skip(
                "Set WILDINTEL_CLASSIFICATION_PROJECT_PK and "
                "WILDINTEL_CLASSIFICATION_COLLECTION_PK to run this test"
            )

        items = []
        for row in component.where_collection_media(int(pk), int(col_pk), page_size=10):
            items.append(row)
            if len(items) >= 5:
                break

        if not items:
            pytest.skip("No media available for this collection")

        assert all(isinstance(row, MediaRecord) for row in items)

    @pytest.mark.e2e
    def test_export_collection_media_returns_list_when_file_none(self, component):
        """export_collection_media() sin file devuelve lista de MediaRecord."""
        pk = _project_pk()
        col_pk = _collection_pk()
        if not pk or not col_pk:
            pytest.skip(
                "Set WILDINTEL_CLASSIFICATION_PROJECT_PK and "
                "WILDINTEL_CLASSIFICATION_COLLECTION_PK to run this test"
            )

        result = component.export_collection_media(int(pk), int(col_pk), file=None)

        assert isinstance(result, list)
        if result:
            assert isinstance(result[0], MediaRecord)

    @pytest.mark.e2e
    def test_export_collection_media_writes_csv(self, component, tmp_path):
        """export_collection_media() escribe CSV y devuelve Path."""
        pk = _project_pk()
        col_pk = _collection_pk()
        if not pk or not col_pk:
            pytest.skip(
                "Set WILDINTEL_CLASSIFICATION_PROJECT_PK and "
                "WILDINTEL_CLASSIFICATION_COLLECTION_PK to run this test"
            )

        out = tmp_path / "collection_media.csv"
        result = component.export_collection_media(int(pk), int(col_pk), file=out)

        assert isinstance(result, Path)
        assert out.exists()
        assert out.stat().st_size > 0


# ── download ──────────────────────────────────────────────────────────────────

class TestDownloadMediaE2E:

    @pytest.fixture(scope="class")
    def component(self, real_api_base):
        return ClassificationMediaComponent(real_api_base)

    @pytest.mark.e2e
    def test_download_media_file_downloads_content(self, component, tmp_path):
        """download_media_file() descarga el fichero y devuelve Path."""
        media_id = _media_id()
        if not media_id:
            pytest.skip("Set WILDINTEL_MEDIA_ID to run this test")

        out = tmp_path / "media.jpg"
        result = component.download_media_file(media_id=int(media_id), file=out)

        assert isinstance(result, Path)
        assert out.exists()
        assert out.stat().st_size > 0

    @pytest.mark.e2e
    def test_download_project_media_files_returns_list(self, component, tmp_path):
        """download_project_media_files() devuelve lista de Path."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.download_project_media_files(
            int(pk), output_dir=tmp_path
        )

        assert isinstance(result, list)

    @pytest.mark.e2e
    def test_download_project_media_files_compress_creates_zip(self, component, tmp_path):
        """download_project_media_files() con compress=True crea un ZIP."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.download_project_media_files(
            int(pk), output_dir=tmp_path, compress=True
        )

        zip_files = list(tmp_path.glob("*.zip"))
        if result:
            assert len(zip_files) == 1

    @pytest.mark.e2e
    def test_download_collection_media_files_returns_list(self, component, tmp_path):
        """download_collection_media_files() devuelve lista de Path."""
        pk = _project_pk()
        col_pk = _collection_pk()
        if not pk or not col_pk:
            pytest.skip(
                "Set WILDINTEL_CLASSIFICATION_PROJECT_PK and "
                "WILDINTEL_CLASSIFICATION_COLLECTION_PK to run this test"
            )

        result = component.download_collection_media_files(
            int(pk), int(col_pk), output_dir=tmp_path
        )

        assert isinstance(result, list)

    @pytest.mark.e2e
    def test_download_collection_media_files_parallel(self, component, tmp_path):
        """download_collection_media_files() con parallel=True descarga correctamente."""
        pk = _project_pk()
        col_pk = _collection_pk()
        if not pk or not col_pk:
            pytest.skip(
                "Set WILDINTEL_CLASSIFICATION_PROJECT_PK and "
                "WILDINTEL_CLASSIFICATION_COLLECTION_PK to run this test"
            )

        result = component.download_collection_media_files(
            int(pk), int(col_pk), output_dir=tmp_path, parallel=True, max_workers=2
        )

        assert isinstance(result, list)