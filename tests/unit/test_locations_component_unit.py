"""
Unit tests for LocationsComponent.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from tests.base_component_tests import ComponentUnitTestBase
from trapper_client import err
from trapper_client.components.locations import LocationsComponent
from trapper_client.schemas import Location, LocationExport

class TestLocationsComponent(ComponentUnitTestBase):
    component_class = LocationsComponent
    schema = Location
    export_schema = LocationExport
    find_pk = 1
    valid_item = {"pk": 1, "name": "Location A"}
    valid_export_item = {
        "_id": 1,
        "locationID": "dona_001",
        "latitude": 37.1,
        "longitude": -6.9,
    }


# ── import_locations ──────────────────────────────────────────────────────────

class TestImportLocations:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return LocationsComponent(client)

    @pytest.fixture
    def csv_file(self, tmp_path):
        path = tmp_path / "locations.csv"
        path.write_text("location_id,name\nloc1,Location 1\n", encoding="utf-8")
        return path

    def _mock_response(self, client, status_code=302, text=""):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        client.session_post_multipart.return_value = response
        return response

    def test_uses_import_endpoint(self, component, client, csv_file):
        """import_locations() postea al endpoint geomap/location/import/."""
        self._mock_response(client)

        component.import_locations(file=csv_file, research_project=7, timezone="Europe/Madrid")

        assert client.session_post_multipart.call_args[0][0] == component.import_endpoint

    def test_sends_csv_file(self, component, client, csv_file):
        """import_locations() envía el CSV bajo la clave 'csv_file'."""
        self._mock_response(client)

        component.import_locations(file=csv_file, research_project=7, timezone="Europe/Madrid")

        files = client.session_post_multipart.call_args.kwargs["files"]
        assert "csv_file" in files
        assert files["csv_file"][0] == csv_file.name
        assert "gpx_file" not in files

    def test_sends_gpx_file_when_provided(self, component, client, csv_file, tmp_path):
        """import_locations() incluye el GPX cuando se especifica."""
        gpx_path = tmp_path / "track.gpx"
        gpx_path.write_text("<gpx></gpx>", encoding="utf-8")
        self._mock_response(client)

        component.import_locations(
            file=csv_file, research_project=7, timezone="Europe/Madrid", gpx_file=gpx_path,
        )

        files = client.session_post_multipart.call_args.kwargs["files"]
        assert "gpx_file" in files
        assert files["gpx_file"][0] == gpx_path.name

    def test_sends_research_project_and_timezone(self, component, client, csv_file):
        """import_locations() envía research_project y timezone."""
        self._mock_response(client)

        component.import_locations(file=csv_file, research_project=7, timezone="Europe/Madrid")

        data = client.session_post_multipart.call_args.kwargs["data"]
        assert data["research_project"] == 7
        assert data["timezone"] == "Europe/Madrid"

    def test_research_project_is_required(self, component, csv_file):
        """import_locations() exige research_project (el form del servidor lo requiere en la práctica,
        pese a declararlo required=False — ver clean_research_project())."""
        with pytest.raises(TypeError):
            component.import_locations(file=csv_file, timezone="Europe/Madrid")

    def test_timezone_is_required(self, component, csv_file):
        """import_locations() exige timezone.

        El servidor lo declara required=False, pero LocationImporter.import_locations()
        persiste con bulk_create() (que se salta la validación normal del modelo) — un
        timezone vacío puede crear locations con datos corruptos que solo revientan
        más tarde, al listarlas (500 al serializar). Se exige aquí para no producir
        ese estado silenciosamente.
        """
        with pytest.raises(TypeError):
            component.import_locations(file=csv_file, research_project=7)

    def test_returns_true_on_redirect(self, component, client, csv_file):
        """import_locations() devuelve True cuando el servidor responde con un redirect."""
        self._mock_response(client, status_code=302)

        result = component.import_locations(file=csv_file, research_project=7, timezone="Europe/Madrid")

        assert result is True

    def test_raises_when_not_redirect(self, component, client, csv_file):
        """import_locations() lanza APIError si la respuesta no es un redirect."""
        self._mock_response(client, status_code=200, text="<html>errors</html>")

        with pytest.raises(err.APIError):
            component.import_locations(file=csv_file, research_project=7, timezone="Europe/Madrid")

    def test_error_message_extracted_from_html(self, component, client, csv_file):
        """import_locations() usa _extract_html_error_text() para el mensaje de la excepción."""
        client._extract_html_error_text.return_value = "You have to select a research project."
        self._mock_response(client, status_code=200, text="<html>...</html>")

        with pytest.raises(err.APIError, match="You have to select a research project."):
            component.import_locations(file=csv_file, research_project=7, timezone="Europe/Madrid")

        client._extract_html_error_text.assert_called_once_with("<html>...</html>")

    def test_returns_false_when_raise_on_error_false(self, component, client, csv_file):
        """import_locations() devuelve False si raise_on_error=False y falla."""
        self._mock_response(client, status_code=200, text="<html>errors</html>")

        result = component.import_locations(
            file=csv_file, research_project=7, timezone="Europe/Madrid", raise_on_error=False,
        )

        assert result is False

    def test_file_is_closed_after_call(self, component, client, csv_file):
        """import_locations() cierra el fichero abierto tras la llamada."""
        self._mock_response(client)

        component.import_locations(file=csv_file, research_project=7, timezone="Europe/Madrid")

        files = client.session_post_multipart.call_args.kwargs["files"]
        handle = files["csv_file"][1]
        assert handle.closed is True


# ── import_locations(split=True) ────────────────────────────────────────────

class TestImportLocationsSplit:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return LocationsComponent(client)

    @pytest.fixture
    def big_csv_file(self, tmp_path):
        path = tmp_path / "locations.csv"
        rows = ["locationID,longitude,latitude"] + [
            f"loc{i},-6.{i},37.{i}" for i in range(50)
        ]
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        return path

    @pytest.fixture(autouse=True)
    def mock_sleep(self):
        """Evita dormir de verdad en cualquier test de esta clase (real chunk_size=50 genera
        muchos chunks, y varios tests no verifican el sleep pero sí lo disparan)."""
        with patch("trapper_client.components.locations.time.sleep") as mock:
            yield mock

    def _mock_response(self, client, status_code=302, text=""):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        return response

    def test_splits_into_multiple_requests(self, component, client, big_csv_file):
        """import_locations(split=True) hace una petición por cada chunk generado."""
        client.session_post_multipart.return_value = self._mock_response(client)

        component.import_locations(
            file=big_csv_file, research_project=7, timezone="Europe/Madrid",
            split=True, chunk_size=50,
        )

        assert client.session_post_multipart.call_count > 1

    def test_every_request_sends_same_form_data(self, component, client, big_csv_file):
        """import_locations(split=True) envía los mismos campos de formulario en cada chunk."""
        client.session_post_multipart.return_value = self._mock_response(client)

        component.import_locations(
            file=big_csv_file, research_project=7, timezone="Europe/Madrid",
            split=True, chunk_size=50,
        )

        for call in client.session_post_multipart.call_args_list:
            assert call.kwargs["data"]["research_project"] == 7
            assert call.kwargs["data"]["timezone"] == "Europe/Madrid"

    def test_sleeps_between_chunks_not_after_last(self, component, client, big_csv_file, mock_sleep):
        """import_locations(split=True) duerme delay segundos entre chunks, no tras el último."""
        client.session_post_multipart.return_value = self._mock_response(client)

        component.import_locations(
            file=big_csv_file, research_project=7, timezone="Europe/Madrid",
            split=True, chunk_size=50, delay=3,
        )

        n_chunks = client.session_post_multipart.call_count
        assert n_chunks > 1
        assert mock_sleep.call_count == n_chunks - 1
        for call in mock_sleep.call_args_list:
            assert call.args == (3,)

    def test_default_delay_is_one_second(self, component, client, big_csv_file, mock_sleep):
        """import_locations(split=True) usa delay=1 por defecto."""
        client.session_post_multipart.return_value = self._mock_response(client)

        component.import_locations(
            file=big_csv_file, research_project=7, timezone="Europe/Madrid",
            split=True, chunk_size=50,
        )

        assert mock_sleep.call_count > 0
        assert all(call.args == (1,) for call in mock_sleep.call_args_list)

    def test_cleans_up_temp_chunk_files(self, component, client, big_csv_file):
        """import_locations(split=True) borra los ficheros temporales de los chunks al terminar."""
        seen_paths = []

        def _capture(endpoint, data, files):
            seen_paths.append(Path(files["csv_file"][1].name))
            return self._mock_response(client)

        client.session_post_multipart.side_effect = _capture

        component.import_locations(
            file=big_csv_file, research_project=7, timezone="Europe/Madrid",
            split=True, chunk_size=50,
        )

        assert seen_paths
        assert all(not p.exists() for p in seen_paths)

    def test_stops_on_first_failure_when_raise_on_error_true(self, component, client, big_csv_file):
        """import_locations(split=True) para en el primer chunk que falla si raise_on_error=True."""
        calls = {"n": 0}

        def _side_effect(endpoint, data, files):
            calls["n"] += 1
            status = 200 if calls["n"] == 2 else 302
            return self._mock_response(client, status_code=status, text="<html>bad</html>")

        client.session_post_multipart.side_effect = _side_effect

        with pytest.raises(err.APIError):
            component.import_locations(
                file=big_csv_file, research_project=7, timezone="Europe/Madrid",
                split=True, chunk_size=50,
            )

        assert client.session_post_multipart.call_count == 2

    def test_continues_on_failure_when_raise_on_error_false(self, component, client, big_csv_file):
        """import_locations(split=True, raise_on_error=False) sigue con el resto de chunks."""
        from trapper_client.csv_chunking import split_csv_by_size
        expected_chunks = len(split_csv_by_size(big_csv_file, max_bytes=50))

        calls = {"n": 0}

        def _side_effect(endpoint, data, files):
            calls["n"] += 1
            status = 200 if calls["n"] == 2 else 302
            return self._mock_response(client, status_code=status, text="<html>bad</html>")

        client.session_post_multipart.side_effect = _side_effect

        result = component.import_locations(
            file=big_csv_file, research_project=7, timezone="Europe/Madrid",
            split=True, chunk_size=50, raise_on_error=False,
        )

        assert result is False
        assert client.session_post_multipart.call_count == expected_chunks

    def test_returns_true_when_all_chunks_succeed(self, component, client, big_csv_file):
        """import_locations(split=True) devuelve True si todos los chunks tienen éxito."""
        client.session_post_multipart.return_value = self._mock_response(client, status_code=302)

        result = component.import_locations(
            file=big_csv_file, research_project=7, timezone="Europe/Madrid",
            split=True, chunk_size=50,
        )

        assert result is True

    def test_split_with_gpx_file_raises_value_error(self, component, big_csv_file, tmp_path):
        """import_locations(split=True, gpx_file=...) no está soportado."""
        gpx_path = tmp_path / "track.gpx"
        gpx_path.write_text("<gpx></gpx>", encoding="utf-8")

        with pytest.raises(ValueError):
            component.import_locations(
                file=big_csv_file, research_project=7, timezone="Europe/Madrid",
                split=True, gpx_file=gpx_path,
            )


# ── import_locations(retry_attempts=...) ──────────────────────────────────────

class TestImportLocationsRetry:
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
        return LocationsComponent(client)

    @pytest.fixture
    def csv_file(self, tmp_path):
        path = tmp_path / "locations.csv"
        path.write_text("locationID,longitude,latitude\nloc1,-6.1,37.1\n", encoding="utf-8")
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

        result = component.import_locations(
            file=csv_file, research_project=7, timezone="Europe/Madrid",
            retry_min_wait=0.01, retry_max_wait=0.02,
        )

        assert result is True
        assert client.session_post_multipart.call_count == 2

    def test_gives_up_after_exhausting_attempts(self, component, client, csv_file):
        """Si todos los intentos fallan por timeout, propaga el error de transporte."""
        client.session_post_multipart.side_effect = httpx.ReadTimeout("timed out", request=None)

        with pytest.raises(httpx.ReadTimeout):
            component.import_locations(
                file=csv_file, research_project=7, timezone="Europe/Madrid",
                retry_attempts=3, retry_min_wait=0.01, retry_max_wait=0.02,
            )

        assert client.session_post_multipart.call_count == 3

    def test_retry_attempts_one_disables_retrying(self, component, client, csv_file):
        """retry_attempts=1 hace una única llamada, sin reintentar."""
        client.session_post_multipart.side_effect = httpx.ReadTimeout("timed out", request=None)

        with pytest.raises(httpx.ReadTimeout):
            component.import_locations(
                file=csv_file, research_project=7, timezone="Europe/Madrid",
                retry_attempts=1, retry_min_wait=0.01, retry_max_wait=0.02,
            )

        assert client.session_post_multipart.call_count == 1

    def test_does_not_retry_non_transport_errors(self, component, client, csv_file):
        """Un error que no sea de transporte (p. ej. un bug interno) no se reintenta."""
        client.session_post_multipart.side_effect = ValueError("not a transport error")

        with pytest.raises(ValueError):
            component.import_locations(
                file=csv_file, research_project=7, timezone="Europe/Madrid",
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
                fh.read(5)  # simulate a partial read before the connection times out
                raise httpx.ReadTimeout("timed out", request=None)
            return self._mock_response()

        client.session_post_multipart.side_effect = _side_effect

        component.import_locations(
            file=csv_file, research_project=7, timezone="Europe/Madrid",
            retry_min_wait=0.01, retry_max_wait=0.02,
        )

        assert positions == [0, 0]