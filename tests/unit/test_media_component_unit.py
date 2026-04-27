"""
Unit tests for ClassificationMediaComponent.

All API calls and file I/O are mocked — no real server or filesystem needed.
"""
from __future__ import annotations

import gzip
import zipfile
import io
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from tests.base_component_tests import ComponentUnitTestBase, paginated_response
from trapper_client.api_query import APIQuery
from trapper_client.components.classification_media import ClassificationMediaComponent
from trapper_client.schemas import MediaRecord, PaginatedResult


# ── datos de prueba ───────────────────────────────────────────────────────────

VALID_MEDIA = {
    "pk": 1,
    "id": 1,
    "mediaID": 1,
    "deploymentID": "r0021-dona_00_01",
    "captureMethod": "activityDetection",
    "timestamp": "2022-07-20T13:16:42+02:00",
    "filePath": "http://example.com/storage/media/1/pfile/",
    "filePublic": False,
    "fileName": "IMG_0001.jpg",
    "fileMediatype": "image/jpeg",
    "favorite": False,
}
PROJECT_PK = 7
COLLECTION_PK = 5
LINK_PK = 99
MEDIA_ID = 1


# ── tests heredados ───────────────────────────────────────────────────────────

class TestClassificationMediaComponent(ComponentUnitTestBase):
    component_class = ClassificationMediaComponent
    schema = MediaRecord
    export_schema = MediaRecord
    find_pk = 1
    valid_item = VALID_MEDIA
    valid_export_item = VALID_MEDIA


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return MagicMock()


@pytest.fixture
def component(client):
    return ClassificationMediaComponent(client)


# ── _resolve_endpoint ─────────────────────────────────────────────────────────

class TestResolveEndpoint:

    @pytest.fixture
    def component(self):
        return ClassificationMediaComponent(MagicMock())

    def test_resolves_project_pk_in_endpoint(self, component):
        """_resolve_endpoint() sustituye {project_pk} correctamente."""
        result = component._resolve_endpoint(PROJECT_PK)
        assert str(PROJECT_PK) in result
        assert "{project_pk}" not in result

    def test_returns_string(self, component):
        """_resolve_endpoint() devuelve un string."""
        assert isinstance(component._resolve_endpoint(PROJECT_PK), str)


# ── _resolve_collection_pk ────────────────────────────────────────────────────

class TestResolveCollectionPk:

    @pytest.fixture
    def component(self, client):
        return ClassificationMediaComponent(client)

    @pytest.fixture
    def client(self):
        return MagicMock()

    def test_returns_link_pk_when_found(self, component):
        """_resolve_collection_pk() devuelve el pk del link cuando la colección existe."""
        mock_link = MagicMock()
        mock_link.collection_pk = COLLECTION_PK
        mock_link.pk = LINK_PK

        mock_result = MagicMock()
        mock_result.results = [mock_link]

        with patch(
            "trapper_client.components.classification_media.ClassificationProjectsCollectionsComponent"
        ) as MockComp:
            instance = MockComp.return_value
            instance.get_all_classification_project.return_value = mock_result

            result = component._resolve_collection_pk(PROJECT_PK, COLLECTION_PK)

        assert result == LINK_PK

    def test_returns_original_pk_when_not_found(self, component):
        """_resolve_collection_pk() devuelve collection_pk original si no encuentra link."""
        mock_result = MagicMock()
        mock_result.results = []

        with patch(
            "trapper_client.components.classification_media.ClassificationProjectsCollectionsComponent"
        ) as MockComp:
            instance = MockComp.return_value
            instance.get_all_classification_project.return_value = mock_result

            result = component._resolve_collection_pk(PROJECT_PK, COLLECTION_PK)

        assert result == COLLECTION_PK


# ── _extract_media_id ─────────────────────────────────────────────────────────

class TestExtractMediaId:

    @pytest.fixture
    def component(self):
        return ClassificationMediaComponent(MagicMock())

    def test_extracts_id_from_dict(self, component):
        """_extract_media_id() extrae el id de un dict."""
        assert component._extract_media_id({"id": 42}) == 42

    def test_extracts_pk_from_dict(self, component):
        """_extract_media_id() extrae el pk si no hay id."""
        assert component._extract_media_id({"pk": 42}) == 42

    def test_extracts_from_model(self, component):
        """_extract_media_id() extrae el id de un modelo Pydantic."""
        mock_model = MagicMock()
        mock_model.model_dump.return_value = {"id": 42}
        assert component._extract_media_id(mock_model) == 42

    def test_returns_none_when_no_id(self, component):
        """_extract_media_id() devuelve None si no hay ningún campo reconocido."""
        assert component._extract_media_id({"other_field": "value"}) is None

    def test_returns_none_for_unknown_type(self, component):
        """_extract_media_id() devuelve None para tipos no reconocidos."""
        assert component._extract_media_id("not_a_media") is None

    def test_converts_string_to_int(self, component):
        """_extract_media_id() convierte strings numéricos a int."""
        assert component._extract_media_id({"id": "42"}) == 42

    def test_returns_none_for_non_numeric_string(self, component):
        """_extract_media_id() devuelve None para strings no numéricos."""
        assert component._extract_media_id({"id": "not_a_number"}) is None


# ── _compress_files ───────────────────────────────────────────────────────────

class TestCompressFiles:

    @pytest.fixture
    def component(self):
        return ClassificationMediaComponent(MagicMock())

    def test_creates_zip_archive(self, component, tmp_path):
        """_compress_files() crea un archivo ZIP con los ficheros indicados."""
        file1 = tmp_path / "file1.jpg"
        file2 = tmp_path / "file2.jpg"
        file1.write_bytes(b"content1")
        file2.write_bytes(b"content2")

        archive = tmp_path / "archive.zip"
        result = component._compress_files([file1, file2], archive_file=archive)

        assert result == archive
        assert archive.exists()
        with zipfile.ZipFile(archive) as zf:
            assert "file1.jpg" in zf.namelist()
            assert "file2.jpg" in zf.namelist()

    def test_creates_temp_zip_when_no_archive_file(self, component, tmp_path):
        """_compress_files() crea un fichero temporal si no se indica archive_file."""
        file1 = tmp_path / "file1.jpg"
        file1.write_bytes(b"content")

        result = component._compress_files([file1])

        assert result.exists()
        assert result.suffix == ".zip"

    def test_skips_nonexistent_files(self, component, tmp_path):
        """_compress_files() ignora ficheros que no existen."""
        real_file = tmp_path / "real.jpg"
        real_file.write_bytes(b"content")
        missing_file = tmp_path / "missing.jpg"

        archive = tmp_path / "archive.zip"
        component._compress_files([real_file, missing_file], archive_file=archive)

        with zipfile.ZipFile(archive) as zf:
            assert "real.jpg" in zf.namelist()
            assert "missing.jpg" not in zf.namelist()


# ── project media ─────────────────────────────────────────────────────────────

class TestProjectMedia:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return ClassificationMediaComponent(client)

    def _expected_endpoint(self, component):
        return component._resolve_endpoint(PROJECT_PK)

    # ── get_project_media ─────────────────────────────────────────────────────

    def test_get_project_media_returns_paginated_result(self, component, client):
        """get_project_media() devuelve PaginatedResult con items de tipo MediaRecord."""
        client.get.return_value = paginated_response([VALID_MEDIA])

        result = component.get_project_media(PROJECT_PK)

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], MediaRecord)

    def test_get_project_media_uses_correct_endpoint(self, component, client):
        """get_project_media() usa el endpoint del proyecto."""
        client.get.return_value = paginated_response([])

        component.get_project_media(PROJECT_PK)

        assert client.get.call_args[0][0] == self._expected_endpoint(component)

    def test_get_project_media_sends_page_and_page_size(self, component, client):
        """get_project_media() envía page y page_size al cliente."""
        client.get.return_value = paginated_response([])

        component.get_project_media(PROJECT_PK, page=2, page_size=25)

        params = client.get.call_args[1]["query"]
        assert params["page"] == 2
        assert params["page_size"] == 25

    def test_get_project_media_passes_extra_kwargs(self, component, client):
        """get_project_media() pasa kwargs como parámetros de consulta."""
        client.get.return_value = paginated_response([])

        component.get_project_media(PROJECT_PK, deployment=12)

        params = client.get.call_args[1]["query"]
        assert params["deployment"] == 12

    def test_get_project_media_validate_false_returns_models(self, component, client):
        """get_project_media() con validate=False construye sin validación."""
        client.get.return_value = paginated_response([VALID_MEDIA])

        result = component.get_project_media(PROJECT_PK, validate=False)

        assert isinstance(result.results[0], MediaRecord)

    # ── where_project_media ───────────────────────────────────────────────────

    def test_where_project_media_returns_api_query(self, component):
        """where_project_media() devuelve un APIQuery."""
        assert isinstance(component.where_project_media(PROJECT_PK), APIQuery)

    def test_where_project_media_uses_correct_endpoint(self, component):
        """where_project_media() usa el endpoint del proyecto."""
        query = component.where_project_media(PROJECT_PK)
        assert query.endpoint == self._expected_endpoint(component)

    def test_where_project_media_uses_media_schema(self, component):
        """where_project_media() usa MediaRecord como schema."""
        query = component.where_project_media(PROJECT_PK)
        assert query.schema is MediaRecord

    def test_where_project_media_passes_page_size(self, component):
        """where_project_media() pasa page_size al APIQuery."""
        query = component.where_project_media(PROJECT_PK, page_size=100)
        assert query._page_size == 100

    def test_where_project_media_passes_extra_kwargs(self, component):
        """where_project_media() pasa kwargs como parámetros de consulta."""
        query = component.where_project_media(PROJECT_PK, deployment=12)
        assert query.query["deployment"] == 12

    def test_where_project_media_validate_false(self, component):
        """where_project_media() pasa validate=False al APIQuery."""
        query = component.where_project_media(PROJECT_PK, validate=False)
        assert query.validate is False

    # ── export_project_media ──────────────────────────────────────────────────

    def test_export_project_media_returns_list_when_file_is_none(self, component, client):
        """export_project_media() devuelve lista de modelos cuando file=None."""
        client.get_all.return_value = paginated_response([VALID_MEDIA])

        result = component.export_project_media(PROJECT_PK, file=None)

        assert isinstance(result, list)
        assert isinstance(result[0], MediaRecord)

    def test_export_project_media_writes_csv_when_file_provided(self, component, client, tmp_path):
        """export_project_media() escribe CSV y devuelve Path cuando se indica file."""
        client.get_all.return_value = paginated_response([VALID_MEDIA])
        out = tmp_path / "media.csv"
        client._select_file.return_value = out
        client._write_csv = MagicMock()

        result = component.export_project_media(PROJECT_PK, file=out)

        assert isinstance(result, Path)
        client._write_csv.assert_called_once()

    def test_export_project_media_uses_correct_endpoint(self, component, client):
        """export_project_media() usa el endpoint del proyecto."""
        client.get_all.return_value = paginated_response([])

        component.export_project_media(PROJECT_PK, file=None)

        assert client.get_all.call_args[0][0] == self._expected_endpoint(component)

    # ── get_project_media_by_id ───────────────────────────────────────────────

    def test_get_project_media_by_id_returns_matching_record(self, component, client):
        """get_project_media_by_id() devuelve el MediaRecord con el id correcto."""
        client.get.return_value = paginated_response([VALID_MEDIA])

        result = component.get_project_media_by_id(PROJECT_PK, MEDIA_ID)

        assert isinstance(result, MediaRecord)

    def test_get_project_media_by_id_returns_none_when_not_found(self, component, client):
        """get_project_media_by_id() devuelve None si no encuentra el media_id."""
        client.get.return_value = paginated_response([VALID_MEDIA])

        result = component.get_project_media_by_id(PROJECT_PK, media_id=999)

        assert result is None

    def test_get_project_media_by_id_returns_none_on_empty_results(self, component, client):
        """get_project_media_by_id() devuelve None si no hay resultados."""
        client.get.return_value = paginated_response([])

        result = component.get_project_media_by_id(PROJECT_PK, MEDIA_ID)

        assert result is None


# ── collection media ──────────────────────────────────────────────────────────

class TestCollectionMedia:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        comp = ClassificationMediaComponent(client)
        # patch _resolve_collection_pk to avoid external dependency
        comp._resolve_collection_pk = MagicMock(return_value=LINK_PK)
        return comp

    def _expected_endpoint(self, component):
        return component._resolve_endpoint(PROJECT_PK)

    # ── get_collection_media ──────────────────────────────────────────────────

    def test_get_collection_media_returns_paginated_result(self, component, client):
        """get_collection_media() devuelve PaginatedResult."""
        client.get.return_value = paginated_response([VALID_MEDIA])

        result = component.get_collection_media(PROJECT_PK, COLLECTION_PK)

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], MediaRecord)

    def test_get_collection_media_uses_correct_endpoint(self, component, client):
        """get_collection_media() usa el endpoint del proyecto."""
        client.get.return_value = paginated_response([])

        component.get_collection_media(PROJECT_PK, COLLECTION_PK)

        assert client.get.call_args[0][0] == self._expected_endpoint(component)

    def test_get_collection_media_sends_collection_filter(self, component, client):
        """get_collection_media() envía el link_pk como parámetro collection."""
        client.get.return_value = paginated_response([])

        component.get_collection_media(PROJECT_PK, COLLECTION_PK)

        params = client.get.call_args[1]["query"]
        assert params["collection"] == LINK_PK

    def test_get_collection_media_resolves_collection_pk(self, component):
        """get_collection_media() llama a _resolve_collection_pk."""
        component.client.get.return_value = paginated_response([])

        component.get_collection_media(PROJECT_PK, COLLECTION_PK)

        component._resolve_collection_pk.assert_called_once_with(PROJECT_PK, COLLECTION_PK)

    # ── where_collection_media ────────────────────────────────────────────────

    def test_where_collection_media_returns_api_query(self, component):
        """where_collection_media() devuelve un APIQuery."""
        assert isinstance(component.where_collection_media(PROJECT_PK, COLLECTION_PK), APIQuery)

    def test_where_collection_media_uses_correct_endpoint(self, component):
        """where_collection_media() usa el endpoint del proyecto."""
        query = component.where_collection_media(PROJECT_PK, COLLECTION_PK)
        assert query.endpoint == self._expected_endpoint(component)

    def test_where_collection_media_sends_collection_filter(self, component):
        """where_collection_media() incluye el link_pk como parámetro collection."""
        query = component.where_collection_media(PROJECT_PK, COLLECTION_PK)
        assert query.query["collection"] == LINK_PK

    def test_where_collection_media_validate_false(self, component):
        """where_collection_media() pasa validate=False al APIQuery."""
        query = component.where_collection_media(PROJECT_PK, COLLECTION_PK, validate=False)
        assert query.validate is False

    # ── export_collection_media ───────────────────────────────────────────────

    def test_export_collection_media_returns_list_when_file_is_none(self, component, client):
        """export_collection_media() devuelve lista de modelos cuando file=None."""
        client.get_all.return_value = paginated_response([VALID_MEDIA])

        result = component.export_collection_media(PROJECT_PK, COLLECTION_PK, file=None)

        assert isinstance(result, list)
        assert isinstance(result[0], MediaRecord)

    def test_export_collection_media_sends_collection_filter(self, component, client):
        """export_collection_media() incluye el link_pk como parámetro collection."""
        client.get_all.return_value = paginated_response([])

        component.export_collection_media(PROJECT_PK, COLLECTION_PK, file=None)

        params = client.get_all.call_args[1]["query"]
        assert params["collection"] == LINK_PK


# ── download_media_file ───────────────────────────────────────────────────────

class TestDownloadMediaFile:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return ClassificationMediaComponent(client)

    def test_download_media_file_writes_content(self, component, client, tmp_path):
        """download_media_file() escribe el contenido de la respuesta en el fichero."""
        mock_response = MagicMock()
        mock_response.content = b"fake_image_data"
        client.make_request.return_value = mock_response

        out = tmp_path / "media.jpg"
        client._select_file.return_value = out

        result = component.download_media_file(media_id=MEDIA_ID, file=out)

        assert result == out
        assert out.read_bytes() == b"fake_image_data"

    def test_download_media_file_uses_correct_endpoint(self, component, client, tmp_path):
        """download_media_file() construye el endpoint con media_id y file_field."""
        mock_response = MagicMock()
        mock_response.content = b"data"
        client.make_request.return_value = mock_response
        client._select_file.return_value = tmp_path / "media.jpg"

        component.download_media_file(media_id=MEDIA_ID, file_field="pfile")

        called_endpoint = client.make_request.call_args[1]["endpoint"]
        assert str(MEDIA_ID) in called_endpoint
        assert "pfile" in called_endpoint

    def test_download_media_file_retries_on_failure(self, component, client, tmp_path):
        """download_media_file() reintenta en caso de fallo."""
        mock_response = MagicMock()
        mock_response.content = b"data"
        client.make_request.side_effect = [Exception("timeout"), mock_response]
        out = tmp_path / "media.jpg"
        client._select_file.return_value = out

        result = component.download_media_file(
            media_id=MEDIA_ID, file=out, retry_attempts=2
        )

        assert client.make_request.call_count == 2
        assert result == out


# ── _download_media_ids ───────────────────────────────────────────────────────

class TestDownloadMediaIds:

    @pytest.fixture
    def component(self):
        comp = ClassificationMediaComponent(MagicMock())
        comp.download_media_file = MagicMock(
            side_effect=lambda media_id, file_field, file, **kw: file
        )
        return comp

    def test_downloads_all_media_ids(self, component, tmp_path):
        """_download_media_ids() descarga todos los media_ids indicados."""
        result = component._download_media_ids(
            media_ids=[1, 2, 3],
            output_path=tmp_path,
        )
        assert component.download_media_file.call_count == 3

    def test_returns_list_of_paths(self, component, tmp_path):
        """_download_media_ids() devuelve lista de Path."""
        result = component._download_media_ids(
            media_ids=[1, 2],
            output_path=tmp_path,
        )
        assert isinstance(result, list)

    def test_skips_failed_downloads(self, component, tmp_path):
        """_download_media_ids() ignora los ficheros que fallan."""
        component.download_media_file.side_effect = [
            tmp_path / "media_1",
            Exception("error"),
            tmp_path / "media_3",
        ]

        result = component._download_media_ids(
            media_ids=[1, 2, 3],
            output_path=tmp_path,
        )

        assert len(result) == 2

    def test_compresses_when_compress_true(self, component, tmp_path):
        """_download_media_ids() crea ZIP cuando compress=True."""
        files = [tmp_path / f"media_{i}" for i in range(2)]
        for f in files:
            f.write_bytes(b"data")

        component.download_media_file.side_effect = files
        archive = tmp_path / "archive.zip"
        component._compress_files = MagicMock(return_value=archive)

        component._download_media_ids(
            media_ids=[1, 2],
            output_path=tmp_path,
            compress=True,
            archive_file=archive,
        )

        component._compress_files.assert_called_once()

    def test_parallel_downloads(self, component, tmp_path):
        """_download_media_ids() ejecuta descargas en paralelo."""
        files = [tmp_path / f"media_{i}" for i in range(3)]
        component.download_media_file.side_effect = files

        result = component._download_media_ids(
            media_ids=[1, 2, 3],
            output_path=tmp_path,
            parallel=True,
            max_workers=2,
        )

        assert len(result) == 3


# ── download_project_media_files ──────────────────────────────────────────────

class TestDownloadProjectMediaFiles:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        comp = ClassificationMediaComponent(client)
        comp._download_media_ids = MagicMock(return_value=[])
        return comp

    def test_download_project_media_files_calls_download(self, component, client, tmp_path):
        """download_project_media_files() llama a _download_media_ids."""
        client.get_all.return_value = paginated_response([VALID_MEDIA])

        component.download_project_media_files(PROJECT_PK, output_dir=tmp_path)

        component._download_media_ids.assert_called_once()

    def test_download_project_media_files_uses_correct_endpoint(self, component, client, tmp_path):
        """download_project_media_files() usa el endpoint del proyecto."""
        client.get_all.return_value = paginated_response([])

        component.download_project_media_files(PROJECT_PK, output_dir=tmp_path)

        called_endpoint = client.get_all.call_args[0][0]
        assert str(PROJECT_PK) in called_endpoint

    def test_download_project_media_files_sets_archive_name(self, component, client, tmp_path):
        """download_project_media_files() genera nombre de archivo ZIP automático."""
        client.get_all.return_value = paginated_response([VALID_MEDIA])

        component.download_project_media_files(
            PROJECT_PK, output_dir=tmp_path, compress=True
        )

        call_kwargs = component._download_media_ids.call_args[1]
        assert f"project_{PROJECT_PK}" in str(call_kwargs["archive_file"])


# ── download_collection_media_files ──────────────────────────────────────────

class TestDownloadCollectionMediaFiles:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        comp = ClassificationMediaComponent(client)
        comp._download_media_ids = MagicMock(return_value=[])
        comp._resolve_collection_pk = MagicMock(return_value=LINK_PK)
        return comp

    def test_download_collection_media_files_calls_download(self, component, client, tmp_path):
        """download_collection_media_files() llama a _download_media_ids."""
        client.get_all.return_value = paginated_response([VALID_MEDIA])

        component.download_collection_media_files(PROJECT_PK, COLLECTION_PK, output_dir=tmp_path)

        component._download_media_ids.assert_called_once()

    def test_download_collection_media_files_sends_collection_filter(self, component, client, tmp_path):
        """download_collection_media_files() envía el link_pk como filtro collection."""
        client.get_all.return_value = paginated_response([])

        component.download_collection_media_files(PROJECT_PK, COLLECTION_PK, output_dir=tmp_path)

        params = client.get_all.call_args[1]["query"]
        assert params["collection"] == LINK_PK

    def test_download_collection_media_files_sets_archive_name(self, component, client, tmp_path):
        """download_collection_media_files() genera nombre de archivo ZIP automático."""
        client.get_all.return_value = paginated_response([VALID_MEDIA])

        component.download_collection_media_files(
            PROJECT_PK, COLLECTION_PK, output_dir=tmp_path, compress=True
        )

        call_kwargs = component._download_media_ids.call_args[1]
        archive_name = str(call_kwargs["archive_file"])
        assert f"project_{PROJECT_PK}" in archive_name
        assert f"collection_{COLLECTION_PK}" in archive_name