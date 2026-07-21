"""
Unit tests for LocationsComponent.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from tests.base_component_tests import ComponentUnitTestBase, paginated_response
from trapper_client import err
from trapper_client.api_query import APIQuery
from trapper_client.components.deployments import DeploymentsComponent
from trapper_client.schemas import  Deployment, DeploymentExport

class TestDeploymentsComponent(ComponentUnitTestBase):
    component_class = DeploymentsComponent
    schema = Deployment
    export_schema = DeploymentExport
    find_pk = 1
    valid_item = {"pk": 1, "name": "Deployment A"}
    valid_export_item = {
        "_id": 1,
        "deployment_id": "dona_001",
        "latitude": 37.1,
        "longitude": -6.9,
    }


COLLECTION_ID = 5


# ── by_collection / export_by_collection ──────────────────────────────────────
#
# Regresión: ambos métodos estaban comentados en el código (el `def` deshabilitado,
# dejando solo el docstring como statement huérfano), pese a estar documentados como
# ejemplo de uso en la propia clase y en TrapperClient. Cualquier llamada real a
# client.deployments.by_collection(...) lanzaba AttributeError.

class TestByCollection:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return DeploymentsComponent(client)

    def test_by_collection_returns_api_query(self, component):
        assert isinstance(component.by_collection(COLLECTION_ID), APIQuery)

    def test_by_collection_uses_component_endpoint(self, component):
        query = component.by_collection(COLLECTION_ID)
        assert query.endpoint == DeploymentsComponent.endpoint

    def test_by_collection_maps_collection_id_to_colls_param(self, component):
        query = component.by_collection(COLLECTION_ID)
        assert query.query["colls"] == COLLECTION_ID

    def test_by_collection_passes_extra_kwargs(self, component):
        query = component.by_collection(COLLECTION_ID, status="Public")
        assert query.query["status"] == "Public"

    def test_by_collection_passes_page_size(self, component):
        query = component.by_collection(COLLECTION_ID, page_size=25)
        assert query._page_size == 25


class TestExportByCollection:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return DeploymentsComponent(client)

    def test_export_by_collection_uses_export_endpoint(self, component, client):
        client.get_all.return_value = paginated_response([])
        component.export_by_collection(COLLECTION_ID, file=None)
        assert client.get_all.call_args[0][0] == DeploymentsComponent.export_endpoint

    def test_export_by_collection_maps_collection_id_to_colls_param(self, component, client):
        client.get_all.return_value = paginated_response([])
        component.export_by_collection(COLLECTION_ID, file=None)
        call_params = client.get_all.call_args[1]["query"]
        assert call_params["colls"] == COLLECTION_ID

    def test_export_by_collection_returns_list_when_file_is_none(self, component, client):
        client.get_all.return_value = paginated_response([{
            "_id": 1, "deployment_id": "dona_001", "latitude": 37.1, "longitude": -6.9,
        }])
        result = component.export_by_collection(COLLECTION_ID, file=None)
        assert isinstance(result, list)
        assert isinstance(result[0], DeploymentExport)


# ── import_deployments ────────────────────────────────────────────────────────

class TestImportDeployments:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return DeploymentsComponent(client)

    @pytest.fixture
    def csv_file(self, tmp_path):
        path = tmp_path / "deployments.csv"
        path.write_text("deployment_id,locationID\ndep1,loc1\n", encoding="utf-8")
        return path

    def _mock_response(self, client, status_code=302, text=""):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        client.session_post_multipart.return_value = response
        return response

    def test_uses_import_endpoint(self, component, client, csv_file):
        """import_deployments() postea al endpoint geomap/deployment/import/."""
        self._mock_response(client)

        component.import_deployments(file=csv_file, timezone="Europe/Madrid", research_project=7)

        assert client.session_post_multipart.call_args[0][0] == component.import_endpoint

    def test_sends_csv_file(self, component, client, csv_file):
        """import_deployments() envía el CSV bajo la clave 'csv_file'."""
        self._mock_response(client)

        component.import_deployments(file=csv_file, timezone="Europe/Madrid", research_project=7)

        files = client.session_post_multipart.call_args.kwargs["files"]
        assert "csv_file" in files
        assert files["csv_file"][0] == csv_file.name

    def test_sends_required_timezone(self, component, client, csv_file):
        """import_deployments() siempre envía timezone (campo obligatorio en el form)."""
        self._mock_response(client)

        component.import_deployments(file=csv_file, timezone="Europe/Madrid", research_project=7)

        data = client.session_post_multipart.call_args.kwargs["data"]
        assert data["timezone"] == "Europe/Madrid"

    def test_research_project_is_required(self, component, csv_file):
        """import_deployments() exige research_project (el form del servidor lo requiere en la
        práctica, pese a declararlo required=False — ver clean_research_project())."""
        with pytest.raises(TypeError):
            component.import_deployments(file=csv_file, timezone="Europe/Madrid")

    def test_sends_research_project_and_classification_project(self, component, client, csv_file):
        """import_deployments() envía research_project (siempre) y classification_project si se indica."""
        self._mock_response(client)

        component.import_deployments(
            file=csv_file, timezone="Europe/Madrid",
            research_project=7, classification_project=3,
        )

        data = client.session_post_multipart.call_args.kwargs["data"]
        assert data["research_project"] == 7
        assert data["classification_project"] == 3

    def test_omits_classification_project_when_not_provided(self, component, client, csv_file):
        """import_deployments() no envía classification_project si no se indica (aquí sí es opcional)."""
        self._mock_response(client)

        component.import_deployments(file=csv_file, timezone="Europe/Madrid", research_project=7)

        data = client.session_post_multipart.call_args.kwargs["data"]
        assert data["research_project"] == 7
        assert "classification_project" not in data

    def test_sends_update_and_create_locations_flags(self, component, client, csv_file):
        """import_deployments() envía update/create_locations/ignore_dst como se indiquen."""
        self._mock_response(client)

        component.import_deployments(
            file=csv_file, timezone="Europe/Madrid", research_project=7,
            update=True, create_locations=True, ignore_dst=True,
        )

        data = client.session_post_multipart.call_args.kwargs["data"]
        assert data["update"] is True
        assert data["create_locations"] is True
        assert data["ignore_DST"] is True

    def test_defaults_for_flags_are_false(self, component, client, csv_file):
        """import_deployments() por defecto no activa update/create_locations/ignore_dst."""
        self._mock_response(client)

        component.import_deployments(file=csv_file, timezone="Europe/Madrid", research_project=7)

        data = client.session_post_multipart.call_args.kwargs["data"]
        assert data["update"] is False
        assert data["create_locations"] is False
        assert data["ignore_DST"] is False

    def test_returns_true_on_redirect(self, component, client, csv_file):
        """import_deployments() devuelve True cuando el servidor responde con un redirect."""
        self._mock_response(client, status_code=302)

        result = component.import_deployments(file=csv_file, timezone="Europe/Madrid", research_project=7)

        assert result is True

    def test_raises_when_not_redirect(self, component, client, csv_file):
        """import_deployments() lanza APIError si la respuesta no es un redirect."""
        self._mock_response(client, status_code=200, text="<html>errors</html>")

        with pytest.raises(err.APIError):
            component.import_deployments(file=csv_file, timezone="Europe/Madrid", research_project=7)

    def test_error_message_extracted_from_html(self, component, client, csv_file):
        """import_deployments() usa _extract_html_error_text() para el mensaje de la excepción."""
        client._extract_html_error_text.return_value = "Select a research project."
        self._mock_response(client, status_code=200, text="<html>...</html>")

        with pytest.raises(err.APIError, match="Select a research project."):
            component.import_deployments(file=csv_file, timezone="Europe/Madrid", research_project=7)

        client._extract_html_error_text.assert_called_once_with("<html>...</html>")

    def test_returns_false_when_raise_on_error_false(self, component, client, csv_file):
        """import_deployments() devuelve False si raise_on_error=False y falla."""
        self._mock_response(client, status_code=200, text="<html>errors</html>")

        result = component.import_deployments(
            file=csv_file, timezone="Europe/Madrid", research_project=7, raise_on_error=False,
        )

        assert result is False

    def test_file_is_closed_after_call(self, component, client, csv_file):
        """import_deployments() cierra el fichero abierto tras la llamada."""
        self._mock_response(client)

        component.import_deployments(file=csv_file, timezone="Europe/Madrid", research_project=7)

        files = client.session_post_multipart.call_args.kwargs["files"]
        handle = files["csv_file"][1]
        assert handle.closed is True


# ── import_deployments(split=True) ───────────────────────────────────────────

class TestImportDeploymentsSplit:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return DeploymentsComponent(client)

    @pytest.fixture
    def big_csv_file(self, tmp_path):
        path = tmp_path / "deployments.csv"
        rows = ["deploymentID,locationID,deploymentStart,deploymentEnd"] + [
            f"dep{i},loc{i},2026-01-01T00:00:00,2026-02-01T00:00:00" for i in range(50)
        ]
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        return path

    @pytest.fixture(autouse=True)
    def mock_sleep(self):
        """Evita dormir de verdad en cualquier test de esta clase."""
        with patch("trapper_client.components.deployments.time.sleep") as mock:
            yield mock

    def _mock_response(self, client, status_code=302, text=""):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        return response

    def test_splits_into_multiple_requests(self, component, client, big_csv_file):
        """import_deployments(split=True) hace una petición por cada chunk generado."""
        client.session_post_multipart.return_value = self._mock_response(client)

        component.import_deployments(
            file=big_csv_file, timezone="Europe/Madrid", research_project=7,
            split=True, chunk_size=50,
        )

        assert client.session_post_multipart.call_count > 1

    def test_every_request_sends_same_form_data(self, component, client, big_csv_file):
        """import_deployments(split=True) envía los mismos campos de formulario en cada chunk."""
        client.session_post_multipart.return_value = self._mock_response(client)

        component.import_deployments(
            file=big_csv_file, timezone="Europe/Madrid", research_project=7,
            split=True, chunk_size=50,
        )

        for call in client.session_post_multipart.call_args_list:
            assert call.kwargs["data"]["research_project"] == 7
            assert call.kwargs["data"]["timezone"] == "Europe/Madrid"

    def test_sleeps_between_chunks_not_after_last(self, component, client, big_csv_file, mock_sleep):
        """import_deployments(split=True) duerme delay segundos entre chunks, no tras el último."""
        client.session_post_multipart.return_value = self._mock_response(client)

        component.import_deployments(
            file=big_csv_file, timezone="Europe/Madrid", research_project=7,
            split=True, chunk_size=50, delay=3,
        )

        n_chunks = client.session_post_multipart.call_count
        assert n_chunks > 1
        assert mock_sleep.call_count == n_chunks - 1
        for call in mock_sleep.call_args_list:
            assert call.args == (3,)

    def test_default_delay_is_one_second(self, component, client, big_csv_file, mock_sleep):
        """import_deployments(split=True) usa delay=1 por defecto."""
        client.session_post_multipart.return_value = self._mock_response(client)

        component.import_deployments(
            file=big_csv_file, timezone="Europe/Madrid", research_project=7,
            split=True, chunk_size=50,
        )

        assert mock_sleep.call_count > 0
        assert all(call.args == (1,) for call in mock_sleep.call_args_list)

    def test_cleans_up_temp_chunk_files(self, component, client, big_csv_file):
        """import_deployments(split=True) borra los ficheros temporales de los chunks al terminar."""
        seen_paths = []

        def _capture(endpoint, data, files):
            seen_paths.append(Path(files["csv_file"][1].name))
            return self._mock_response(client)

        client.session_post_multipart.side_effect = _capture

        component.import_deployments(
            file=big_csv_file, timezone="Europe/Madrid", research_project=7,
            split=True, chunk_size=50,
        )

        assert seen_paths
        assert all(not p.exists() for p in seen_paths)

    def test_stops_on_first_failure_when_raise_on_error_true(self, component, client, big_csv_file):
        """import_deployments(split=True) para en el primer chunk que falla si raise_on_error=True."""
        calls = {"n": 0}

        def _side_effect(endpoint, data, files):
            calls["n"] += 1
            status = 200 if calls["n"] == 2 else 302
            return self._mock_response(client, status_code=status, text="<html>bad</html>")

        client.session_post_multipart.side_effect = _side_effect

        with pytest.raises(err.APIError):
            component.import_deployments(
                file=big_csv_file, timezone="Europe/Madrid", research_project=7,
                split=True, chunk_size=50,
            )

        assert client.session_post_multipart.call_count == 2

    def test_continues_on_failure_when_raise_on_error_false(self, component, client, big_csv_file):
        """import_deployments(split=True, raise_on_error=False) sigue con el resto de chunks."""
        from trapper_client.csv_chunking import split_csv_by_size
        expected_chunks = len(split_csv_by_size(big_csv_file, max_bytes=50))

        calls = {"n": 0}

        def _side_effect(endpoint, data, files):
            calls["n"] += 1
            status = 200 if calls["n"] == 2 else 302
            return self._mock_response(client, status_code=status, text="<html>bad</html>")

        client.session_post_multipart.side_effect = _side_effect

        result = component.import_deployments(
            file=big_csv_file, timezone="Europe/Madrid", research_project=7,
            split=True, chunk_size=50, raise_on_error=False,
        )

        assert result is False
        assert client.session_post_multipart.call_count == expected_chunks

    def test_returns_true_when_all_chunks_succeed(self, component, client, big_csv_file):
        """import_deployments(split=True) devuelve True si todos los chunks tienen éxito."""
        client.session_post_multipart.return_value = self._mock_response(client, status_code=302)

        result = component.import_deployments(
            file=big_csv_file, timezone="Europe/Madrid", research_project=7,
            split=True, chunk_size=50,
        )

        assert result is True


# ── import_deployments(retry_attempts=...) ────────────────────────────────────

class TestImportDeploymentsRetry:
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
        return DeploymentsComponent(client)

    @pytest.fixture
    def csv_file(self, tmp_path):
        path = tmp_path / "deployments.csv"
        path.write_text("deploymentID,locationID\ndep1,loc1\n", encoding="utf-8")
        return path

    def _mock_response(self, status_code=302, text=""):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        return response

    def test_retries_on_transport_error_and_succeeds(self, component, client, csv_file):
        """Ante un timeout transitorio, reintenta y tiene éxito sin propagar el error."""
        calls = {"n": 0}

        def _side_effect(endpoint, data, files):
            calls["n"] += 1
            if calls["n"] == 1:
                raise httpx.ReadTimeout("timed out", request=None)
            return self._mock_response()

        client.session_post_multipart.side_effect = _side_effect

        result = component.import_deployments(
            file=csv_file, timezone="Europe/Madrid", research_project=7,
            retry_min_wait=0.01, retry_max_wait=0.02,
        )

        assert result is True
        assert client.session_post_multipart.call_count == 2

    def test_gives_up_after_exhausting_attempts(self, component, client, csv_file):
        """Si todos los intentos fallan por timeout, propaga el error de transporte."""
        client.session_post_multipart.side_effect = httpx.ReadTimeout("timed out", request=None)

        with pytest.raises(httpx.ReadTimeout):
            component.import_deployments(
                file=csv_file, timezone="Europe/Madrid", research_project=7,
                retry_attempts=3, retry_min_wait=0.01, retry_max_wait=0.02,
            )

        assert client.session_post_multipart.call_count == 3

    def test_retry_attempts_one_disables_retrying(self, component, client, csv_file):
        """retry_attempts=1 hace una única llamada, sin reintentar."""
        client.session_post_multipart.side_effect = httpx.ReadTimeout("timed out", request=None)

        with pytest.raises(httpx.ReadTimeout):
            component.import_deployments(
                file=csv_file, timezone="Europe/Madrid", research_project=7,
                retry_attempts=1, retry_min_wait=0.01, retry_max_wait=0.02,
            )

        assert client.session_post_multipart.call_count == 1

    def test_does_not_retry_non_transport_errors(self, component, client, csv_file):
        """Un error que no sea de transporte (p. ej. un bug interno) no se reintenta."""
        client.session_post_multipart.side_effect = ValueError("not a transport error")

        with pytest.raises(ValueError):
            component.import_deployments(
                file=csv_file, timezone="Europe/Madrid", research_project=7,
                retry_min_wait=0.01, retry_max_wait=0.02,
            )

        assert client.session_post_multipart.call_count == 1

    def test_rewinds_file_before_each_retry_attempt(self, component, client, csv_file):
        """Cada reintento relee el fichero desde el principio, no desde donde
        se quedó la lectura parcial que provocó el timeout anterior."""
        calls = {"n": 0}
        positions = []

        def _side_effect(endpoint, data, files):
            calls["n"] += 1
            fh = files["csv_file"][1]
            positions.append(fh.tell())
            if calls["n"] == 1:
                fh.read(5)
                raise httpx.ReadTimeout("timed out", request=None)
            return self._mock_response()

        client.session_post_multipart.side_effect = _side_effect

        component.import_deployments(
            file=csv_file, timezone="Europe/Madrid", research_project=7,
            retry_min_wait=0.01, retry_max_wait=0.02,
        )

        assert positions == [0, 0]