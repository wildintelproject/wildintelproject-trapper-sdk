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

import httpx
import pytest

from tests.base_component_tests import ComponentUnitTestBase, paginated_response
from trapper_client import err
from trapper_client.api_query import APIQuery
from trapper_client.components.classification_media import ClassificationMediaComponent
from trapper_client.schemas import Media, PaginatedResult


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
FILE_URL = "http://example.com/storage/media/1/pfile/"


# ── tests heredados ───────────────────────────────────────────────────────────

class TestClassificationMediaComponent(ComponentUnitTestBase):
    component_class = ClassificationMediaComponent
    schema = Media
    export_schema = Media
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
            "trapper_client.components.classification_media.ClassificationProjectsComponent"
        ) as MockComp:
            instance = MockComp.return_value
            instance.get_all_project_collections.return_value = mock_result

            result = component._resolve_collection_pk(PROJECT_PK, COLLECTION_PK)

        assert result == LINK_PK

    def test_returns_original_pk_when_not_found(self, component):
        """_resolve_collection_pk() devuelve collection_pk original si no encuentra link."""
        mock_result = MagicMock()
        mock_result.results = []

        with patch(
            "trapper_client.components.classification_media.ClassificationProjectsComponent"
        ) as MockComp:
            instance = MockComp.return_value
            instance.get_all_project_collections.return_value = mock_result

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
        """get_project_media() devuelve PaginatedResult con items de tipo Media."""
        client.get.return_value = paginated_response([VALID_MEDIA])

        result = component.get_project_media(PROJECT_PK)

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], Media)

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

        assert isinstance(result.results[0], Media)

    # ── where_project_media ───────────────────────────────────────────────────

    def test_where_project_media_returns_api_query(self, component):
        """where_project_media() devuelve un APIQuery."""
        assert isinstance(component.where_project_media(PROJECT_PK), APIQuery)

    def test_where_project_media_uses_correct_endpoint(self, component):
        """where_project_media() usa el endpoint del proyecto."""
        query = component.where_project_media(PROJECT_PK)
        assert query.endpoint == self._expected_endpoint(component)

    def test_where_project_media_uses_media_schema(self, component):
        """where_project_media() usa Media como schema."""
        query = component.where_project_media(PROJECT_PK)
        assert query.schema is Media

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
        assert isinstance(result[0], Media)

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
        """get_project_media_by_id() devuelve el Media con el id correcto."""
        client.get.return_value = paginated_response([VALID_MEDIA])

        result = component.get_project_media_by_id(PROJECT_PK, MEDIA_ID)

        assert isinstance(result, Media)

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
        assert isinstance(result.results[0], Media)

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
        assert isinstance(result[0], Media)

    def test_export_collection_media_sends_collection_filter(self, component, client):
        """export_collection_media() incluye el link_pk como parámetro collection."""
        client.get_all.return_value = paginated_response([])

        component.export_collection_media(PROJECT_PK, COLLECTION_PK, file=None)

        params = client.get_all.call_args[1]["query"]
        assert params["collection"] == LINK_PK


# ── download_media_file ───────────────────────────────────────────────────────

class TestDownloadMediaFile:

    @staticmethod
    def _component(handler, tmp_path=None):
        client = MagicMock()
        client._client = httpx.Client(transport=httpx.MockTransport(handler))
        client._select_file.side_effect = lambda f: Path(f) if f else Path(tmp_path) / "temp.bin"
        return ClassificationMediaComponent(client), client

    def test_writes_content(self, tmp_path):
        """download_media_file() escribe el cuerpo de la respuesta en el fichero."""
        component, _ = self._component(lambda r: httpx.Response(200, content=b"fake_image_data"))
        out = tmp_path / "media.jpg"

        assert component.download_media_file(file_url=FILE_URL, file=out) == out
        assert out.read_bytes() == b"fake_image_data"
        assert not list(tmp_path.glob("*.part"))

    def test_uses_file_url_as_is_and_sends_no_token(self, tmp_path):
        """Pide file_url tal cual (con su ?rt=) y no manda la cabecera del token de la API.

        Regresión: antes reconstruía la ruta a partir de media_id apuntando a un endpoint inexistente,
        sin el token ?rt= que exige la vista para recursos privados.
        """
        seen = []
        component, _ = self._component(lambda r: seen.append(r) or httpx.Response(200, content=b"x"))

        component.download_media_file(file_url=FILE_URL, file=tmp_path / "m.jpg")

        assert str(seen[0].url) == FILE_URL
        assert "authorization" not in seen[0].headers

    def test_retries_on_network_error(self, tmp_path):
        """Un fallo de red se reintenta."""
        calls = []

        def handler(request):
            calls.append(1)
            if len(calls) == 1:
                raise httpx.ConnectError("boom")
            return httpx.Response(200, content=b"data")

        component, _ = self._component(handler)
        out = tmp_path / "m.jpg"

        assert component.download_media_file(FILE_URL, out, retry_attempts=2, retry_min_wait=0, retry_max_wait=0) == out
        assert len(calls) == 2

    def test_retries_on_503(self, tmp_path):
        """502/503/504 se reintentan."""
        answers = [httpx.Response(503), httpx.Response(200, content=b"ok")]
        component, _ = self._component(lambda r: answers.pop(0))
        out = tmp_path / "m.jpg"

        component.download_media_file(FILE_URL, out, retry_attempts=2, retry_min_wait=0, retry_max_wait=0)

        assert out.read_bytes() == b"ok"

    def test_does_not_retry_a_404(self, tmp_path):
        """Un 404 es NotFoundError y no se reintenta."""
        calls = []
        component, _ = self._component(lambda r: calls.append(1) or httpx.Response(404))

        with pytest.raises(err.NotFoundError):
            component.download_media_file(FILE_URL, tmp_path / "m.jpg", retry_attempts=3, retry_min_wait=0, retry_max_wait=0)

        assert len(calls) == 1
        assert not (tmp_path / "m.jpg").exists()

    def test_a_cut_download_leaves_no_file(self, tmp_path):
        """Si el cuerpo se corta, no queda ni el fichero final ni el .part."""

        class Cut(httpx.SyncByteStream):
            def __iter__(self):
                yield b"half"
                raise httpx.ReadError("cut")

        component, _ = self._component(lambda r: httpx.Response(200, stream=Cut()))
        out = tmp_path / "m.jpg"

        with pytest.raises(httpx.ReadError):
            component.download_media_file(FILE_URL, out, retry_attempts=1)

        assert not out.exists()
        assert not list(tmp_path.glob("*.part"))


# ── _download_media_files ─────────────────────────────────────────────────────

class TestDownloadMediaFiles:

    @pytest.fixture
    def component(self):
        comp = ClassificationMediaComponent(MagicMock())
        comp.download_media_file = MagicMock(
            side_effect=lambda file_url, file, **kw: file
        )
        return comp

    def test_downloads_all_media_rows(self, component, tmp_path):
        """_download_media_files() descarga todos los pares (id, url) indicados."""
        result = component._download_media_files(
            media_rows=[(1, "http://x/1"), (2, "http://x/2"), (3, "http://x/3")],
            output_path=tmp_path,
        )
        assert component.download_media_file.call_count == 3

    def test_passes_file_url_to_download_media_file(self, component, tmp_path):
        """_download_media_files() pasa la url de cada fila, no el id."""
        component._download_media_files(
            media_rows=[(1, "http://x/1")],
            output_path=tmp_path,
        )
        call_kwargs = component.download_media_file.call_args[1]
        assert call_kwargs["file_url"] == "http://x/1"

    def test_returns_list_of_paths(self, component, tmp_path):
        """_download_media_files() devuelve lista de Path."""
        result = component._download_media_files(
            media_rows=[(1, "http://x/1"), (2, "http://x/2")],
            output_path=tmp_path,
        )
        assert isinstance(result, list)

    def test_skips_failed_downloads(self, component, tmp_path):
        """_download_media_files() ignora los ficheros que fallan."""
        component.download_media_file.side_effect = [
            tmp_path / "media_1",
            Exception("error"),
            tmp_path / "media_3",
        ]

        result = component._download_media_files(
            media_rows=[(1, "http://x/1"), (2, "http://x/2"), (3, "http://x/3")],
            output_path=tmp_path,
        )

        assert len(result) == 2

    def test_compresses_when_compress_true(self, component, tmp_path):
        """_download_media_files() crea ZIP cuando compress=True."""
        files = [tmp_path / f"media_{i}" for i in range(2)]
        for f in files:
            f.write_bytes(b"data")

        component.download_media_file.side_effect = files
        archive = tmp_path / "archive.zip"
        component._compress_files = MagicMock(return_value=archive)

        component._download_media_files(
            media_rows=[(1, "http://x/1"), (2, "http://x/2")],
            output_path=tmp_path,
            compress=True,
            archive_file=archive,
        )

        component._compress_files.assert_called_once()

    def test_parallel_downloads(self, component, tmp_path):
        """_download_media_files() ejecuta descargas en paralelo."""
        files = [tmp_path / f"media_{i}" for i in range(3)]
        component.download_media_file.side_effect = files

        result = component._download_media_files(
            media_rows=[(1, "http://x/1"), (2, "http://x/2"), (3, "http://x/3")],
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
        comp._download_media_files = MagicMock(return_value=[])
        return comp

    def test_download_project_media_files_calls_download(self, component, client, tmp_path):
        """download_project_media_files() llama a _download_media_files."""
        client.get_all.return_value = paginated_response([VALID_MEDIA])

        component.download_project_media_files(PROJECT_PK, output_dir=tmp_path)

        component._download_media_files.assert_called_once()

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

        call_kwargs = component._download_media_files.call_args[1]
        assert f"project_{PROJECT_PK}" in str(call_kwargs["archive_file"])


# ── download_collection_media_files ──────────────────────────────────────────

class TestDownloadCollectionMediaFiles:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        comp = ClassificationMediaComponent(client)
        comp._download_media_files = MagicMock(return_value=[])
        comp._resolve_collection_pk = MagicMock(return_value=LINK_PK)
        return comp

    def test_download_collection_media_files_calls_download(self, component, client, tmp_path):
        """download_collection_media_files() llama a _download_media_files."""
        client.get_all.return_value = paginated_response([VALID_MEDIA])

        component.download_collection_media_files(PROJECT_PK, COLLECTION_PK, output_dir=tmp_path)

        component._download_media_files.assert_called_once()

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

        call_kwargs = component._download_media_files.call_args[1]
        archive_name = str(call_kwargs["archive_file"])
        assert f"project_{PROJECT_PK}" in archive_name
        assert f"collection_{COLLECTION_PK}" in archive_name