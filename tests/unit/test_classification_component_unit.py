"""
Unit tests for ClassificationsComponent.

All API calls are mocked — no real server needed.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from tests.base_component_tests import ComponentUnitTestBase, paginated_response
from trapper_client import err
from trapper_client.api_query import APIQuery
from trapper_client.components.classifications import ClassificationsComponent
from trapper_client.schemas import (
    ClassificationImportResponse,
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


# ── import_classifications ────────────────────────────────────────────────────

class TestImportClassifications:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return ClassificationsComponent(client)

    @pytest.fixture
    def csv_file(self, tmp_path):
        path = tmp_path / "observations.csv"
        path.write_text("_id,species\n1,fox\n", encoding="utf-8")
        return path

    def _mock_response(self, client, payload, status_code=201):
        response = MagicMock()
        response.status_code = status_code
        response.json.return_value = payload
        client.post_multipart.return_value = response
        return response

    def test_uses_import_endpoint(self, component, client, csv_file):
        """import_classifications() postea al endpoint .../classifications/import/."""
        self._mock_response(client, {"data": {"message": "ok", "errors": None, "task_id": None}})

        component.import_classifications(project_id=PROJECT_PK, file=csv_file)

        endpoint = client.post_multipart.call_args.kwargs["endpoint"]
        assert endpoint == f"{component.endpoint.rstrip('/')}/import/"

    def test_sends_project_id_and_flags(self, component, client, csv_file):
        """import_classifications() envía project_id y los flags booleanos."""
        self._mock_response(client, {"data": {}})

        component.import_classifications(
            project_id=PROJECT_PK, file=csv_file, approve=False, import_bboxes=False,
        )

        data = client.post_multipart.call_args.kwargs["data"]
        assert data["project_id"] == PROJECT_PK
        assert data["approve"] is False
        assert data["import_bboxes"] is False
        assert "import_ai_classifications" not in data

    def test_omits_import_ai_classifications_key_when_false(self, component, client, csv_file):
        """import_classifications() no envía import_ai_classifications si es False.

        El servidor lee ese flag del cuerpo crudo antes de pasar por el form,
        con un chequeo de verdad en Python plano: un string "False" enviado por
        multipart seguiría siendo truthy ahí, así que se omite la clave.
        """
        self._mock_response(client, {"data": {}})

        component.import_classifications(project_id=PROJECT_PK, file=csv_file, import_ai_classifications=False)

        data = client.post_multipart.call_args.kwargs["data"]
        assert "import_ai_classifications" not in data
        assert "ai_provider_id" not in data

    def test_sends_ai_provider_id_when_importing_ai_classifications(self, component, client, csv_file):
        """import_classifications() incluye ai_provider_id cuando import_ai_classifications=True."""
        self._mock_response(client, {"data": {}})

        component.import_classifications(
            project_id=PROJECT_PK, file=csv_file, import_ai_classifications=True, ai_provider_id=3,
        )

        data = client.post_multipart.call_args.kwargs["data"]
        assert data["import_ai_classifications"] is True
        assert data["ai_provider_id"] == 3

    def test_raises_if_ai_classifications_without_provider(self, component, csv_file):
        """import_classifications() lanza ValueError si falta ai_provider_id."""
        with pytest.raises(ValueError):
            component.import_classifications(
                project_id=PROJECT_PK, file=csv_file, import_ai_classifications=True,
            )

    def test_sends_file_as_multipart_file(self, component, client, csv_file):
        """import_classifications() envía el fichero bajo la clave 'file'."""
        self._mock_response(client, {"data": {}})

        component.import_classifications(project_id=PROJECT_PK, file=csv_file)

        files = client.post_multipart.call_args.kwargs["files"]
        assert "file" in files
        assert files["file"][0] == csv_file.name

    def test_returns_validated_response(self, component, client, csv_file):
        """import_classifications() devuelve ClassificationImportResponse cuando validate=True."""
        self._mock_response(client, {"data": {"message": "ok", "errors": None, "task_id": "abc"}})

        result = component.import_classifications(project_id=PROJECT_PK, file=csv_file)

        assert isinstance(result, ClassificationImportResponse)
        assert result.data.task_id == "abc"

    def test_returns_raw_dict_when_validate_false(self, component, client, csv_file):
        """import_classifications() devuelve el dict crudo cuando validate=False."""
        payload = {"data": {"message": "ok", "errors": None, "task_id": None}}
        self._mock_response(client, payload)

        result = component.import_classifications(project_id=PROJECT_PK, file=csv_file, validate=False)

        assert result == payload

    def test_always_calls_post_multipart_with_raise_on_error_false(self, component, client, csv_file):
        """import_classifications() siempre llama a post_multipart con raise_on_error=False.

        Este endpoint devuelve su propio cuerpo de error estructurado
        ({"data": {"message", "errors", "task_id"}}), que no encaja con el
        formato genérico que espera APIClientBase._handle_error
        ({"_error": {"message": ...}}) — dejar que post_multipart lance el
        error automáticamente mostraría el dict crudo en vez del mensaje real
        del servidor. Por eso import_classifications() gestiona el error él
        mismo a partir del payload, independientemente de lo que el llamante
        pida en su propio raise_on_error.
        """
        self._mock_response(client, {"data": {}})

        component.import_classifications(project_id=PROJECT_PK, file=csv_file, raise_on_error=True)
        assert client.post_multipart.call_args.kwargs["raise_on_error"] is False

        component.import_classifications(project_id=PROJECT_PK, file=csv_file, raise_on_error=False)
        assert client.post_multipart.call_args.kwargs["raise_on_error"] is False

    def test_raises_clean_error_message_on_400(self, component, client, csv_file):
        """import_classifications() lanza un error con el message/errors reales del servidor."""
        self._mock_response(
            client,
            {"data": {
                "message": "Bad request",
                "errors": {"observations_csv": ["This field is required."]},
                "task_id": None,
            }},
            status_code=400,
        )

        with pytest.raises(err.BadRequestError) as exc_info:
            component.import_classifications(project_id=PROJECT_PK, file=csv_file)

        message = str(exc_info.value)
        assert "Bad request" in message
        assert "observations_csv" in message
        assert "This field is required." in message

    def test_maps_404_to_not_found_error(self, component, client, csv_file):
        """import_classifications() mapea un 404 a err.NotFoundError."""
        self._mock_response(
            client,
            {"data": {"message": "The requested classification project does not exist.", "errors": None, "task_id": None}},
            status_code=404,
        )

        with pytest.raises(err.NotFoundError, match="does not exist"):
            component.import_classifications(project_id=PROJECT_PK, file=csv_file)

    def test_returns_payload_without_raising_when_raise_on_error_false(self, component, client, csv_file):
        """import_classifications(raise_on_error=False) devuelve el payload crudo en vez de lanzar."""
        payload = {"data": {"message": "Bad request", "errors": {"project_id": ["invalid"]}, "task_id": None}}
        self._mock_response(client, payload, status_code=400)

        result = component.import_classifications(project_id=PROJECT_PK, file=csv_file, raise_on_error=False)

        assert result == payload

    def _mock_html_error_response(self, client, status_code=500, html="<!DOCTYPE html><html><body><h1>Oops, Server error</h1></body></html>"):
        """Simula un 500 real del servidor cuya respuesta es HTML, no JSON."""
        response = MagicMock()
        response.status_code = status_code
        response.json.side_effect = ValueError("Expecting value: line 1 column 1 (char 0)")
        response.text = html
        client.post_multipart.return_value = response
        return response

    def test_raises_clear_error_instead_of_crashing_on_non_json_500(self, component, client, csv_file):
        """import_classifications() no debe reventar con JSONDecodeError cuando el
        servidor devuelve un 500 real con una página HTML de error en vez de JSON
        (bug reportado: un fallo no controlado del servidor hacía crashear al
        cliente con json.decoder.JSONDecodeError en vez de mostrar un error claro).
        """
        self._mock_html_error_response(client)

        with pytest.raises(err.APIError) as exc_info:
            component.import_classifications(project_id=PROJECT_PK, file=csv_file)

        message = str(exc_info.value)
        assert "non-JSON response" in message
        assert "Oops, Server error" in message

    def test_returns_synthesized_dict_on_non_json_500_when_raise_on_error_false(self, component, client, csv_file):
        """Con raise_on_error=False y un 500 en HTML, devuelve un dict sintético en
        vez de lanzar JSONDecodeError."""
        self._mock_html_error_response(client)

        result = component.import_classifications(project_id=PROJECT_PK, file=csv_file, raise_on_error=False)

        assert "Oops, Server error" in result["data"]["message"]
        assert result["data"]["errors"] is None
        assert result["data"]["task_id"] is None

    def test_raises_clear_error_when_success_status_has_non_json_body(self, component, client, csv_file):
        """Si el servidor responde 2xx pero el cuerpo no es JSON (caso inesperado
        pero posible), se lanza un err.APIError claro en vez de un JSONDecodeError
        crudo."""
        self._mock_html_error_response(client, status_code=200, html="<html>not json</html>")

        with pytest.raises(err.APIError, match="isn't JSON"):
            component.import_classifications(project_id=PROJECT_PK, file=csv_file)


# ── import_classifications(split=True) ────────────────────────────────────────

class TestImportClassificationsSplit:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return ClassificationsComponent(client)

    @pytest.fixture
    def big_csv_file(self, tmp_path):
        path = tmp_path / "observations.csv"
        rows = ["_id,species"] + [f"{i},fox" for i in range(50)]
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        return path

    @pytest.fixture(autouse=True)
    def mock_sleep(self):
        """Evita dormir de verdad (chunk_size=50 genera muchos chunks en estos tests)."""
        with patch("trapper_client.components.classifications.time.sleep") as mock:
            yield mock

    def _mock_response(self, client, payload=None, status_code=201):
        if payload is None:
            payload = {"data": {"message": "ok", "errors": None, "task_id": None}}
        response = MagicMock()
        response.status_code = status_code
        response.json.return_value = payload
        client.post_multipart.return_value = response
        return response

    def test_splits_into_multiple_requests(self, component, client, big_csv_file):
        """import_classifications(split=True) hace una petición por cada chunk generado."""
        self._mock_response(client)

        component.import_classifications(
            project_id=PROJECT_PK, file=big_csv_file, split=True, chunk_size=50,
        )

        assert client.post_multipart.call_count > 1

    def test_every_request_sends_same_form_data(self, component, client, big_csv_file):
        """import_classifications(split=True) envía los mismos campos de formulario en cada chunk."""
        self._mock_response(client)

        component.import_classifications(
            project_id=PROJECT_PK, file=big_csv_file, split=True, chunk_size=50,
        )

        for call in client.post_multipart.call_args_list:
            assert call.kwargs["data"]["project_id"] == PROJECT_PK

    def test_returns_list_of_results_one_per_chunk(self, component, client, big_csv_file):
        """import_classifications(split=True) devuelve una lista con un resultado por chunk."""
        self._mock_response(client)

        results = component.import_classifications(
            project_id=PROJECT_PK, file=big_csv_file, split=True, chunk_size=50,
        )

        assert isinstance(results, list)
        assert len(results) == client.post_multipart.call_count
        assert all(isinstance(r, ClassificationImportResponse) for r in results)

    def test_sleeps_between_chunks_not_after_last(self, component, client, big_csv_file, mock_sleep):
        """import_classifications(split=True) duerme delay segundos entre chunks, no tras el último."""
        self._mock_response(client)

        component.import_classifications(
            project_id=PROJECT_PK, file=big_csv_file, split=True, chunk_size=50, delay=3,
        )

        n_chunks = client.post_multipart.call_count
        assert n_chunks > 1
        assert mock_sleep.call_count == n_chunks - 1
        for call in mock_sleep.call_args_list:
            assert call.args == (3,)

    def test_default_delay_is_one_second(self, component, client, big_csv_file, mock_sleep):
        """import_classifications(split=True) usa delay=1 por defecto."""
        self._mock_response(client)

        component.import_classifications(
            project_id=PROJECT_PK, file=big_csv_file, split=True, chunk_size=50,
        )

        assert mock_sleep.call_count > 0
        assert all(call.args == (1,) for call in mock_sleep.call_args_list)

    def test_cleans_up_temp_chunk_files(self, component, client, big_csv_file):
        """import_classifications(split=True) borra los ficheros temporales de los chunks al terminar."""
        seen_paths = []

        def _capture(endpoint, data, files, raise_on_error):
            seen_paths.append(Path(files["file"][1].name))
            response = MagicMock()
            response.status_code = 201
            response.json.return_value = {"data": {"message": "ok", "errors": None, "task_id": None}}
            return response

        client.post_multipart.side_effect = _capture

        component.import_classifications(
            project_id=PROJECT_PK, file=big_csv_file, split=True, chunk_size=50,
        )

        assert seen_paths
        assert all(not p.exists() for p in seen_paths)

    def test_stops_on_first_failure_when_raise_on_error_true(self, component, client, big_csv_file):
        """import_classifications(split=True) para en el primer chunk que falla si raise_on_error=True."""
        calls = {"n": 0}

        def _side_effect(endpoint, data, files, raise_on_error):
            calls["n"] += 1
            response = MagicMock()
            if calls["n"] == 2:
                response.status_code = 400
                response.json.return_value = {
                    "data": {"message": "Bad request", "errors": {"file": ["bad"]}, "task_id": None},
                }
            else:
                response.status_code = 201
                response.json.return_value = {"data": {"message": "ok", "errors": None, "task_id": None}}
            return response

        client.post_multipart.side_effect = _side_effect

        with pytest.raises(err.BadRequestError):
            component.import_classifications(
                project_id=PROJECT_PK, file=big_csv_file, split=True, chunk_size=50,
            )

        assert client.post_multipart.call_count == 2

    def test_continues_on_failure_when_raise_on_error_false(self, component, client, big_csv_file):
        """import_classifications(split=True, raise_on_error=False) sube todos los chunks
        aunque alguno falle, y refleja el fallo en el resultado de ese chunk."""
        from trapper_client.csv_chunking import split_csv_by_size

        expected_chunks = len(split_csv_by_size(big_csv_file, max_bytes=50))
        calls = {"n": 0}

        def _side_effect(endpoint, data, files, raise_on_error):
            calls["n"] += 1
            response = MagicMock()
            if calls["n"] == 2:
                response.status_code = 400
                response.json.return_value = {
                    "data": {"message": "Bad request", "errors": {"file": ["bad"]}, "task_id": None},
                }
            else:
                response.status_code = 201
                response.json.return_value = {"data": {"message": "ok", "errors": None, "task_id": None}}
            return response

        client.post_multipart.side_effect = _side_effect

        results = component.import_classifications(
            project_id=PROJECT_PK, file=big_csv_file, split=True, chunk_size=50, raise_on_error=False,
        )

        assert client.post_multipart.call_count == expected_chunks
        assert len(results) == expected_chunks
        assert results[1]["data"]["message"] == "Bad request"


# ── import_classifications(retry_attempts=...) ────────────────────────────────

class TestImportClassificationsRetry:
    """Reintentos ante fallos de red (timeout/conexión) al subir un chunk.

    Reintenta con tenacity solo ante errores de transporte (httpx.TransportError,
    p. ej. un timeout del servidor cuando el chunk sigue siendo demasiado grande) —
    nunca ante respuestas HTTP de error (esas son fallos de validación que un
    reintento no puede arreglar).
    """

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return ClassificationsComponent(client)

    @pytest.fixture
    def csv_file(self, tmp_path):
        path = tmp_path / "observations.csv"
        path.write_text("_id,species\n1,fox\n", encoding="utf-8")
        return path

    def _mock_response(self, status_code=201):
        response = MagicMock()
        response.status_code = status_code
        response.json.return_value = {"data": {"message": "ok", "errors": None, "task_id": None}}
        return response

    def test_retries_on_transport_error_and_succeeds(self, component, client, csv_file):
        """Ante un timeout transitorio, reintenta y tiene éxito sin propagar el error."""
        calls = {"n": 0}

        def _side_effect(endpoint, data, files, raise_on_error):
            calls["n"] += 1
            if calls["n"] == 1:
                raise httpx.ReadTimeout("timed out", request=None)
            return self._mock_response()

        client.post_multipart.side_effect = _side_effect

        result = component.import_classifications(
            project_id=PROJECT_PK, file=csv_file,
            retry_min_wait=0.01, retry_max_wait=0.02,
        )

        assert result.data.message == "ok"
        assert client.post_multipart.call_count == 2

    def test_gives_up_after_exhausting_attempts(self, component, client, csv_file):
        """Si todos los intentos fallan por timeout, propaga el error de transporte."""
        client.post_multipart.side_effect = httpx.ReadTimeout("timed out", request=None)

        with pytest.raises(httpx.ReadTimeout):
            component.import_classifications(
                project_id=PROJECT_PK, file=csv_file,
                retry_attempts=3, retry_min_wait=0.01, retry_max_wait=0.02,
            )

        assert client.post_multipart.call_count == 3

    def test_retry_attempts_one_disables_retrying(self, component, client, csv_file):
        """retry_attempts=1 hace una única llamada, sin reintentar."""
        client.post_multipart.side_effect = httpx.ReadTimeout("timed out", request=None)

        with pytest.raises(httpx.ReadTimeout):
            component.import_classifications(
                project_id=PROJECT_PK, file=csv_file,
                retry_attempts=1, retry_min_wait=0.01, retry_max_wait=0.02,
            )

        assert client.post_multipart.call_count == 1

    def test_does_not_retry_non_transport_errors(self, component, client, csv_file):
        """Un error que no sea de transporte (p. ej. un bug interno) no se reintenta."""
        client.post_multipart.side_effect = ValueError("not a transport error")

        with pytest.raises(ValueError):
            component.import_classifications(
                project_id=PROJECT_PK, file=csv_file,
                retry_min_wait=0.01, retry_max_wait=0.02,
            )

        assert client.post_multipart.call_count == 1

    def test_rewinds_file_before_each_retry_attempt(self, component, client, csv_file):
        """Cada reintento relee el fichero desde el principio, no desde donde
        se quedó la lectura parcial que provocó el timeout anterior."""
        calls = {"n": 0}
        positions = []

        def _side_effect(endpoint, data, files, raise_on_error):
            calls["n"] += 1
            fh = files["file"][1]
            positions.append(fh.tell())
            if calls["n"] == 1:
                fh.read(5)
                raise httpx.ReadTimeout("timed out", request=None)
            return self._mock_response()

        client.post_multipart.side_effect = _side_effect

        component.import_classifications(
            project_id=PROJECT_PK, file=csv_file,
            retry_min_wait=0.01, retry_max_wait=0.02,
        )

        assert positions == [0, 0]


# ── regresión: classificationTimestamp="" en las filas de export ─────────────
#
# Bug real reportado: get_project_results()/export_project_results() con
# camtrapdp=False reventaba con un ValidationError de pydantic en cuanto una
# fila traía classificationTimestamp vacío (columna opcional del CSV/JSON
# de exportación) — el campo era Optional[datetime] pero le faltaba el mismo
# saneamiento "" -> None que ya tenían el resto de campos opcionales del mismo
# schema (empty_str_to_none/empty_numeric_to_none).

class TestClassificationTimestampEmptyString:

    def _base_row(self, **overrides):
        row = dict(VALID_EXPORT_RECORD)
        row["_id"] = 42
        row["classificationTimestamp"] = ""
        row.update(overrides)
        return row

    def test_camtrapdp_flavor_accepts_empty_classification_timestamp(self):
        """ClassificationResultRecordCamtrapDP acepta classificationTimestamp=''."""
        result = ClassificationResultRecordCamtrapDP.model_validate(self._base_row())
        assert result.classificationTimestamp is None

    def test_trapper_flavor_accepts_empty_classification_timestamp(self):
        """ClassificationResultRecordTrapper acepta classificationTimestamp=''."""
        result = ClassificationResultRecordTrapper.model_validate(self._base_row())
        assert result.classificationTimestamp is None

    def test_union_type_adapter_accepts_empty_classification_timestamp(self):
        """El Union (como lo usa _to_model en base.py) valida bien la fila real reportada."""
        from pydantic import TypeAdapter
        adapter = TypeAdapter(ClassificationRecordExport)
        result = adapter.validate_python(self._base_row())
        assert result.classificationTimestamp is None

    def test_non_empty_classification_timestamp_still_parses(self):
        """classificationTimestamp con un valor real sigue parseando a datetime."""
        row = self._base_row(classificationTimestamp="2026-01-01T08:00:00")
        result = ClassificationResultRecordTrapper.model_validate(row)
        assert result.classificationTimestamp is not None