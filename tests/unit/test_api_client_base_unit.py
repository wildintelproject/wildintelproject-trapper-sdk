"""
Unit tests for APIClientBase.

All requests are mocked — no real server is needed.
"""
from __future__ import annotations

import gzip
import bz2
import io
import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import httpx

from trapper_client.api_client_base import APIClientBase
from trapper_client import err


# ── helpers ───────────────────────────────────────────────────────────────────

def make_response(
    status_code: int = 200,
    json_data: dict | list | None = None,
    content: bytes | None = None,
    content_type: str = "application/json",
) -> MagicMock:
    """Construye un mock de httpx.Response."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.headers = {"Content-Type": content_type}

    if json_data is not None:
        response.json.return_value = json_data
        response.content = json.dumps(json_data).encode()
        response.text = json.dumps(json_data)
    elif content is not None:
        response.content = content
        response.text = content.decode("utf-8", errors="replace")
        response.json.side_effect = ValueError("Not JSON")
    else:
        response.content = b""
        response.text = ""

    return response


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def token_client():
    """Cliente con token fijo para tests unitarios."""
    return APIClientBase(
        access_token="test-token",
        base_url="https://example.com",
        verify_ssl=True,
        timeout=30,
    )


@pytest.fixture
def basic_auth_client():
    """Cliente con usuario y contraseña fijos para tests unitarios."""
    return APIClientBase(
        user_name="user",
        user_password="pass",
        base_url="https://example.com",
        verify_ssl=True,
        timeout=30,
    )


# ── __init__ / autenticación ──────────────────────────────────────────────────

def test_init_raises_if_no_auth():
    """Se lanza ValueError si no se proporciona ni token ni usuario/contraseña."""
    with pytest.raises(ValueError, match="Token or user/password must be provided"):
        APIClientBase(base_url="https://example.com")


def test_init_accepts_token():
    """Se instancia correctamente con solo un token."""
    client = APIClientBase(access_token="abc", base_url="https://example.com")
    assert client.access_token == "abc"


def test_init_accepts_user_password():
    """Se instancia correctamente con usuario y contraseña."""
    client = APIClientBase(user_name="u", user_password="p", base_url="https://example.com")
    assert client.user_name == "u"


def test_init_verify_ssl_default_is_true():
    """verify_ssl es True por defecto."""
    client = APIClientBase(access_token="tok", base_url="https://example.com")
    assert client.verify_ssl is True


def test_init_timeout_default_is_30():
    """timeout es 30 por defecto."""
    client = APIClientBase(access_token="tok", base_url="https://example.com")
    assert client.timeout == 30


def test_auth_returns_token_header(token_client):
    """_auth() devuelve cabecera Authorization con token."""
    headers, auth = token_client._auth()
    assert headers == {"Authorization": "Token test-token"}
    assert auth is None


def test_auth_returns_basic_auth_tuple(basic_auth_client):
    """_auth() devuelve tupla (user, password) para basic auth."""
    headers, auth = basic_auth_client._auth()
    assert headers == {}
    assert auth == ("user", "pass")


def test_auth_raises_if_no_credentials():
    """_auth() lanza ValueError si no hay credenciales configuradas."""
    client = APIClientBase.__new__(APIClientBase)
    client.access_token = None
    client.user_name = None
    client.user_password = None
    with pytest.raises(ValueError):
        client._auth()


# ── _validate_method ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("method", ["GET", "POST", "PATCH", "PUT", "DELETE"])
def test_validate_method_accepts_valid_methods(token_client, method):
    """_validate_method() no lanza para métodos HTTP válidos."""
    token_client._validate_method(method)


def test_validate_method_raises_for_invalid(token_client):
    """_validate_method() lanza ValueError para métodos no soportados."""
    with pytest.raises(ValueError, match="Invalid method"):
        token_client._validate_method("HEAD")


# ── make_request ──────────────────────────────────────────────────────────────

def test_make_request_returns_response_on_success(token_client):
    """make_request() devuelve el Response cuando el status es 2xx."""
    mock_resp = make_response(200, json_data={"results": []})
    token_client._client.request = MagicMock(return_value=mock_resp)

    result = token_client.make_request("/api/test/", method="GET")

    assert result is mock_resp


def test_make_request_calls_session_with_correct_url(token_client):
    """make_request() construye la URL correctamente desde base_url y endpoint."""
    mock_resp = make_response(200, json_data={})
    token_client._client.request = MagicMock(return_value=mock_resp)

    token_client.make_request("/api/locations/", method="GET")

    call_kwargs = token_client._client.request.call_args.kwargs
    assert call_kwargs["url"] == "https://example.com/api/locations/"


def test_make_request_uses_absolute_url_as_is(token_client):
    """make_request() no antepone base_url cuando endpoint ya es una URL absoluta.

    Necesario para descargar ficheros de media: el campo ``filePath`` que
    devuelve la API ya es una URL absoluta completa (con el token de acceso
    ``?rt=`` embebido para recursos privados); anteponerle base_url de nuevo
    generaría una URL rota.
    """
    mock_resp = make_response(200, json_data={})
    token_client._client.request = MagicMock(return_value=mock_resp)

    absolute_url = "https://media.example.org/storage/resource/media/1/file/?rt=tok123"
    token_client.make_request(absolute_url, method="GET")

    call_kwargs = token_client._client.request.call_args.kwargs
    assert call_kwargs["url"] == absolute_url


def test_client_is_configured_with_timeout(token_client):
    """El httpx.Client se construye con el timeout configurado."""
    assert token_client._client.timeout.read == 30


def test_client_is_configured_with_verify_ssl(token_client):
    """verify_ssl queda almacenado en el cliente y se pasa al httpx.Client."""
    assert token_client.verify_ssl is True


def test_make_request_raises_on_404(token_client):
    """make_request() lanza excepción mapeada para 404."""
    mock_resp = make_response(404, json_data={"_error": {"message": "Not found"}})
    token_client._client.request = MagicMock(return_value=mock_resp)

    with pytest.raises(Exception):
        token_client.make_request("/api/locations/999/", method="GET")


def test_make_request_returns_response_when_raise_on_error_false(token_client):
    """make_request() devuelve el Response en lugar de lanzar si raise_on_error=False."""
    mock_resp = make_response(404, json_data={"_error": {"message": "Not found"}})
    token_client._client.request = MagicMock(return_value=mock_resp)

    result = token_client.make_request("/api/missing/", method="GET", raise_on_error=False)

    assert result.status_code == 404


# ── get ───────────────────────────────────────────────────────────────────────

def test_get_returns_paginated_dict(token_client):
    """get() devuelve dict con claves pagination y results."""
    payload = {
        "pagination": {"page": 1, "pages": 1, "page_size": 10, "count": 2},
        "results": [{"pk": 1}, {"pk": 2}],
    }
    mock_resp = make_response(200, json_data=payload)
    token_client._client.request = MagicMock(return_value=mock_resp)

    result = token_client.get("/api/locations/")

    assert "pagination" in result
    assert "results" in result
    assert len(result["results"]) == 2


def test_get_merges_kwargs_into_query(token_client):
    """get() pasa kwargs adicionales como parámetros de consulta."""
    mock_resp = make_response(200, json_data={"pagination": {}, "results": []})
    token_client._client.request = MagicMock(return_value=mock_resp)

    token_client.get("/api/locations/", page_size=25, search="test")

    call_params = token_client._client.request.call_args.kwargs["params"]
    assert call_params["page_size"] == 25
    assert call_params["search"] == "test"


def test_get_wraps_list_response_in_envelope(token_client):
    """get() envuelve una lista JSON en el sobre pagination/results."""
    mock_resp = make_response(200, json_data=[{"pk": 1}, {"pk": 2}])
    token_client._client.request = MagicMock(return_value=mock_resp)

    result = token_client.get("/api/locations/")

    assert result["pagination"]["count"] == 2
    assert len(result["results"]) == 2


# ── get_one ───────────────────────────────────────────────────────────────────

def test_get_one_returns_raw_dict(token_client):
    """get_one() devuelve el dict crudo del servidor sin envolver."""
    payload = {"pk": 42, "name": "Location A"}
    mock_resp = make_response(200, json_data=payload)
    token_client._client.request = MagicMock(return_value=mock_resp)

    result = token_client.get_one("/api/locations/42/")

    assert result == payload
    assert result["pk"] == 42


# ── get_all / get_all_pages ───────────────────────────────────────────────────

def test_get_all_pages_single_page(token_client):
    """get_all_pages() devuelve todos los resultados si hay una sola página."""
    payload = {
        "pagination": {"page": 1, "pages": 1, "page_size": 10, "count": 3},
        "results": [{"pk": 1}, {"pk": 2}, {"pk": 3}],
    }
    mock_resp = make_response(200, json_data=payload)
    token_client._client.request = MagicMock(return_value=mock_resp)

    result = token_client.get_all_pages("/api/locations/")

    assert len(result["results"]) == 3


def test_get_all_pages_merges_multiple_pages(token_client):
    """get_all_pages() concatena resultados de múltiples páginas."""
    page1 = {
        "pagination": {"page": 1, "pages": 2, "page_size": 2, "count": 4},
        "results": [{"pk": 1}, {"pk": 2}],
    }
    page2 = {
        "pagination": {"page": 2, "pages": 2, "page_size": 2, "count": 4},
        "results": [{"pk": 3}, {"pk": 4}],
    }
    token_client._client.request = MagicMock(
        side_effect=[
            make_response(200, json_data=page1),
            make_response(200, json_data=page2),
        ]
    )

    result = token_client.get_all_pages("/api/locations/")

    assert len(result["results"]) == 4
    assert result["results"][-1]["pk"] == 4


def test_get_all_pages_does_not_include_page_in_initial_query(token_client):
    """get_all_pages() elimina el parámetro page de la consulta inicial."""
    payload = {
        "pagination": {"page": 1, "pages": 1, "count": 1},
        "results": [{"pk": 1}],
    }
    mock_resp = make_response(200, json_data=payload)
    token_client._client.request = MagicMock(return_value=mock_resp)

    token_client.get_all_pages("/api/locations/", query={"page": 3, "page_size": 10})

    call_params = token_client._client.request.call_args.kwargs["params"]
    assert "page" not in call_params


# ── export ────────────────────────────────────────────────────────────────────

def test_export_returns_list_when_file_is_none_and_json(token_client):
    """export() devuelve lista de dicts si file=None y la respuesta es JSON."""
    payload = {
        "pagination": {"page": 1, "pages": 1, "count": 2},
        "results": [{"pk": 1, "name": "A"}, {"pk": 2, "name": "B"}],
    }
    mock_resp = make_response(200, json_data=payload)
    token_client._client.request = MagicMock(return_value=mock_resp)

    result = token_client.export("/api/locations/export/", file=None)

    assert isinstance(result, list)
    assert len(result) == 2


def test_export_writes_csv_when_file_provided(token_client, tmp_path):
    """export() escribe CSV y devuelve Path cuando se indica file."""
    payload = {
        "pagination": {"page": 1, "pages": 1, "count": 2},
        "results": [{"pk": 1, "name": "A"}, {"pk": 2, "name": "B"}],
    }
    mock_resp = make_response(200, json_data=payload)
    token_client._client.request = MagicMock(return_value=mock_resp)

    out = tmp_path / "output.csv"
    result = token_client.export("/api/locations/export/", file=out)

    assert isinstance(result, Path)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "pk" in content
    assert "name" in content


def test_export_writes_direct_csv_response(token_client, tmp_path):
    """export() escribe CSV directamente cuando el servidor devuelve text/csv."""
    csv_content = b"pk,name\n1,Alpha\n2,Beta\n"
    mock_resp = make_response(200, content=csv_content, content_type="text/csv")
    token_client._client.request = MagicMock(return_value=mock_resp)

    out = tmp_path / "output.csv"
    result = token_client.export("/api/locations/export/", file=out)

    assert isinstance(result, Path)
    assert "Alpha" in out.read_text(encoding="utf-8")


# ── _extract_csv_text ─────────────────────────────────────────────────────────

def test_extract_csv_text_plain_csv(token_client):
    """_extract_csv_text() devuelve texto de respuesta text/csv."""
    csv_content = b"pk,name\n1,A\n"
    mock_resp = make_response(200, content=csv_content, content_type="text/csv")

    result = token_client._extract_csv_text(mock_resp)

    assert "pk,name" in result
    assert "1,A" in result


def test_extract_csv_text_from_gzip(token_client):
    """_extract_csv_text() descomprime gzip correctamente."""
    csv_content = b"pk,name\n1,A\n"
    compressed = gzip.compress(csv_content)
    mock_resp = make_response(200, content=compressed, content_type="application/gzip")

    result = token_client._extract_csv_text(mock_resp)

    assert "pk,name" in result


def test_extract_csv_text_from_bzip2(token_client):
    """_extract_csv_text() descomprime bzip2 correctamente."""
    csv_content = b"pk,name\n1,A\n"
    compressed = bz2.compress(csv_content)
    mock_resp = make_response(200, content=compressed, content_type="application/x-bzip2")

    result = token_client._extract_csv_text(mock_resp)

    assert "pk,name" in result


def test_extract_csv_text_from_zip(token_client):
    """_extract_csv_text() extrae el CSV del interior de un ZIP."""
    csv_content = b"pk,name\n1,A\n"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("data.csv", csv_content.decode("utf-8"))
    zip_bytes = buffer.getvalue()

    mock_resp = make_response(200, content=zip_bytes, content_type="application/zip")

    result = token_client._extract_csv_text(mock_resp)

    assert "pk,name" in result


def test_extract_csv_text_raises_if_zip_has_no_csv(token_client):
    """_extract_csv_text() lanza APIError si el ZIP no contiene CSV."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("readme.txt", "nothing here")
    zip_bytes = buffer.getvalue()

    mock_resp = make_response(200, content=zip_bytes, content_type="application/zip")

    with pytest.raises(err.APIError):
        token_client._extract_csv_text(mock_resp)


def test_extract_csv_text_raises_for_unsupported_type(token_client):
    """_extract_csv_text() lanza APIError para content types no soportados."""
    mock_resp = make_response(200, content=b"<html/>", content_type="text/html")

    with pytest.raises(err.APIError):
        token_client._extract_csv_text(mock_resp)


# ── is_* helpers ──────────────────────────────────────────────────────────────

def test_is_json_true_for_json_content_type(token_client):
    """is_json() devuelve True para application/json."""
    mock_resp = make_response(200, json_data={}, content_type="application/json")
    assert token_client.is_json(mock_resp) is True


def test_is_json_false_for_csv_content_type(token_client):
    """is_json() devuelve False para text/csv."""
    mock_resp = make_response(200, content=b"a,b", content_type="text/csv")
    assert token_client.is_json(mock_resp) is False


def test_is_csv_true_for_csv_content_type(token_client):
    """is_csv() devuelve True para text/csv."""
    mock_resp = make_response(200, content=b"a,b", content_type="text/csv")
    assert token_client.is_csv(mock_resp) is True


def test_is_zip_true_for_zip_magic_bytes(token_client):
    """is_zip() detecta ZIP por magic bytes aunque el content type no lo indique."""
    mock_resp = make_response(200, content=b"PK\x03\x04rest", content_type="application/octet-stream")
    assert token_client.is_zip(mock_resp) is True


def test_is_gzip_true_for_gzip_magic_bytes(token_client):
    """is_gzip() detecta gzip por magic bytes."""
    mock_resp = make_response(200, content=b"\x1f\x8brest", content_type="application/octet-stream")
    assert token_client.is_gzip(mock_resp) is True


def test_is_bzip2_true_for_bzip2_magic_bytes(token_client):
    """is_bzip2() detecta bzip2 por magic bytes."""
    mock_resp = make_response(200, content=b"BZrest", content_type="application/octet-stream")
    assert token_client.is_bzip2(mock_resp) is True


# ── _write_csv ────────────────────────────────────────────────────────────────

def test_write_csv_creates_file_with_header(token_client, tmp_path):
    """_write_csv() escribe cabecera y filas correctamente."""
    rows = [{"pk": 1, "name": "Alpha"}, {"pk": 2, "name": "Beta"}]
    out = tmp_path / "test.csv"

    token_client._write_csv(rows, out)

    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0] == "name,pk"   # fieldnames ordenados alfabéticamente
    assert len(lines) == 3         # cabecera + 2 filas


def test_write_csv_empty_rows_creates_empty_file(token_client, tmp_path):
    """_write_csv() crea fichero vacío si rows está vacío."""
    out = tmp_path / "empty.csv"
    token_client._write_csv([], out)

    assert out.exists()
    assert out.read_text(encoding="utf-8") == ""


# ── _merge_query_params ───────────────────────────────────────────────────────

def test_merge_query_params_combines_dicts(token_client):
    """_merge_query_params() combina query base y kwargs extra."""
    result = token_client._merge_query_params({"page": 1}, {"page_size": 25})
    assert result == {"page": 1, "page_size": 25}


def test_merge_query_params_extra_overrides_base(token_client):
    """_merge_query_params() deja que extra sobreescriba claves de query."""
    result = token_client._merge_query_params({"page_size": 10}, {"page_size": 50})
    assert result["page_size"] == 50


def test_merge_query_params_returns_none_when_both_empty(token_client):
    """_merge_query_params() devuelve None cuando ambos están vacíos."""
    result = token_client._merge_query_params(None, {})
    assert result is None


# ── _paginate ─────────────────────────────────────────────────────────────────

def test_paginate_returns_correct_slice(token_client):
    """_paginate() devuelve el slice correcto para la página indicada."""
    items = list(range(25))
    assert token_client._paginate(items, page=1, per_page=10) == list(range(10))
    assert token_client._paginate(items, page=2, per_page=10) == list(range(10, 20))
    assert token_client._paginate(items, page=3, per_page=10) == list(range(20, 25))


# ── _handle_error ─────────────────────────────────────────────────────────────

def test_handle_error_raises_mapped_exception(token_client):
    """_handle_error() lanza la excepción mapeada para el status code."""
    mock_resp = make_response(404, json_data={"_error": {"message": "Not found"}})

    with pytest.raises(Exception):
        token_client._handle_error(mock_resp, raise_on_error=True)


def test_handle_error_returns_response_when_not_raising(token_client):
    """_handle_error() devuelve Response cuando raise_on_error=False."""
    mock_resp = make_response(500, json_data={"_error": {"message": "Server error"}})

    result = token_client._handle_error(mock_resp, raise_on_error=False)

    assert result is mock_resp


# ── HTTP verb shortcuts ───────────────────────────────────────────────────────

@pytest.mark.parametrize("verb,method", [
    ("post", "POST"),
    ("patch", "PATCH"),
    ("put", "PUT"),
    ("delete", "DELETE"),
])
def test_http_verb_shortcuts_call_make_request(token_client, verb, method):
    """post/patch/put/delete() llaman a make_request con el método correcto."""
    mock_resp = make_response(200, json_data={})
    token_client._client.request = MagicMock(return_value=mock_resp)

    getattr(token_client, verb)("/api/test/", body={"key": "value"})

    call_kwargs = token_client._client.request.call_args.kwargs
    assert call_kwargs["method"] == method


# ── post_multipart ────────────────────────────────────────────────────────────

def test_post_multipart_sends_data_and_files(token_client):
    """post_multipart() envía data y files a httpx.Client.request como POST."""
    mock_resp = make_response(201, json_data={"data": {"message": "ok"}})
    token_client._client.request = MagicMock(return_value=mock_resp)

    files = {"file": ("obs.csv", b"a,b\n1,2", "text/csv")}
    result = token_client.post_multipart("/api/import/", data={"approve": True}, files=files)

    assert result is mock_resp
    call_kwargs = token_client._client.request.call_args.kwargs
    assert call_kwargs["method"] == "POST"
    assert call_kwargs["data"] == {"approve": True}
    assert call_kwargs["files"] is files


def test_post_multipart_builds_url_from_base_url(token_client):
    """post_multipart() construye la URL a partir de base_url y el endpoint."""
    mock_resp = make_response(201, json_data={})
    token_client._client.request = MagicMock(return_value=mock_resp)

    token_client.post_multipart("/api/import/", data={}, files={})

    call_kwargs = token_client._client.request.call_args.kwargs
    assert call_kwargs["url"] == "https://example.com/api/import/"


def test_post_multipart_raises_on_error(token_client):
    """post_multipart() lanza una excepción mapeada si la respuesta falla."""
    mock_resp = make_response(400, json_data={"_error": {"message": "Bad request"}})
    token_client._client.request = MagicMock(return_value=mock_resp)

    with pytest.raises(Exception):
        token_client.post_multipart("/api/import/", data={}, files={})


def test_post_multipart_returns_response_when_raise_on_error_false(token_client):
    """post_multipart() devuelve la respuesta si raise_on_error=False."""
    mock_resp = make_response(400, json_data={"_error": {"message": "Bad request"}})
    token_client._client.request = MagicMock(return_value=mock_resp)

    result = token_client.post_multipart("/api/import/", data={}, files={}, raise_on_error=False)

    assert result is mock_resp


# ── session auth (cookie/CSRF, para vistas Django clásicas) ──────────────────

def _fake_login_get(client):
    """Simula que el GET al login setea la cookie csrftoken."""
    def _get(url, *a, **kw):
        client._client.cookies.set("csrftoken", "csrf-abc")
        return MagicMock()
    return _get


def _fake_login_post(client, status_code=302, set_sessionid=True):
    """Simula que el POST de login setea la cookie sessionid en éxito."""
    def _post(url, *a, **kw):
        if set_sessionid:
            client._client.cookies.set("sessionid", "session-abc")
        resp = MagicMock()
        resp.status_code = status_code
        return resp
    return _post


def test_csrf_cookie_value_raises_if_missing(token_client):
    """_csrf_cookie_value() lanza APIError si no hay cookie csrftoken."""
    with pytest.raises(err.APIError):
        token_client._csrf_cookie_value()


def test_csrf_cookie_value_returns_cookie(token_client):
    """_csrf_cookie_value() devuelve el valor de la cookie csrftoken."""
    token_client._client.cookies.set("csrftoken", "abc123")

    assert token_client._csrf_cookie_value() == "abc123"


def test_csrf_cookie_value_falls_back_to_cached_web_token(token_client):
    """_csrf_cookie_value() usa el token cacheado si no hay cookie csrftoken.

    Cubre servidores con CSRF_USE_SESSIONS=True (u otros casos donde la
    cookie no llega, p.ej. un proxy que la descarta) — el token scrapeado
    del HTML durante session_login() se cachea y sigue funcionando.
    """
    token_client._web_csrf_token = "scraped-token"

    assert token_client._csrf_cookie_value() == "scraped-token"


def test_csrf_token_from_html_extracts_value(token_client):
    """_csrf_token_from_html() extrae el value del input csrfmiddlewaretoken."""
    html = '<form><input type="hidden" name="csrfmiddlewaretoken" value="abc123XYZ"></form>'

    assert token_client._csrf_token_from_html(html) == "abc123XYZ"


def test_csrf_token_from_html_returns_none_when_missing(token_client):
    """_csrf_token_from_html() devuelve None si no encuentra el input."""
    assert token_client._csrf_token_from_html("<html><body>no form here</body></html>") is None


# ── _extract_html_error_text ──────────────────────────────────────────────────

def test_extract_html_error_text_finds_alert_danger(token_client):
    """_extract_html_error_text() extrae el texto de un bloque alert-danger (common/table_errors.html)."""
    html = (
        '<div class="alert alert-danger">'
        "<p><strong>Error:</strong> Unfortunately, your table could not be imported.</p>"
        "</div>"
    )

    result = token_client._extract_html_error_text(html)

    assert "could not be imported" in result


def test_extract_html_error_text_finds_django_form_errors(token_client):
    """_extract_html_error_text() extrae errores de formulario (clean_research_project(), etc.)."""
    html = (
        '<ul class="errorlist">'
        "<li>You have to select a research project.</li>"
        "</ul>"
    )

    result = token_client._extract_html_error_text(html)

    assert "You have to select a research project." in result


def test_extract_html_error_text_deduplicates_blocks(token_client):
    """_extract_html_error_text() no repite el mismo mensaje si aparece varias veces."""
    html = (
        '<div class="alert alert-danger">Same message</div>'
        '<div class="alert alert-danger">Same message</div>'
    )

    result = token_client._extract_html_error_text(html)

    assert result.count("Same message") == 1


def test_extract_html_error_text_falls_back_to_body_text(token_client):
    """_extract_html_error_text() cae a un snippet del <body> si no hay marcadores conocidos."""
    html = "<html><head><title>Trapper</title></head><body>Something unexpected happened</body></html>"

    result = token_client._extract_html_error_text(html)

    assert "Something unexpected happened" in result
    assert "Trapper" not in result  # el <head> no debe colarse


def test_extract_html_error_text_respects_max_len(token_client):
    """_extract_html_error_text() trunca a max_len caracteres."""
    html = "<html><body>" + ("x" * 2000) + "</body></html>"

    result = token_client._extract_html_error_text(html, max_len=50)

    assert len(result) == 50


# ── _extract_frictionless_errors (common/table_errors.html's embedded report) ─

def _table_errors_page(report_json: str) -> str:
    """Reconstruye la forma real de common/table_errors.html con un report embebido."""
    return (
        '<div class="alert alert-danger">'
        "<p><strong>Error:</strong> Unfortunately, your table could not be imported; "
        "correct all the errors listed below and try again. "
        "Please note that the number of reported errors is limited to 100.</p>"
        "</div>"
        '<div class="col-md-12" style="padding:0;" id="report"></div>'
        '<script type="module">\n'
        f"    const report = {report_json};\n"
        "    const element = document.getElementById(\"report\");\n"
        "</script>"
    )


def test_extract_frictionless_errors_parses_embedded_report(token_client):
    """_extract_frictionless_errors() extrae los mensajes de report.tasks[].errors[]."""
    report = {
        "valid": False,
        "tasks": [
            {
                "errors": [
                    {"type": "constraint-error", "message": "locationID 'dona-001' already exists"},
                    {"type": "type-error", "message": "longitude must be a number"},
                ]
            }
        ],
    }
    html = _table_errors_page(json.dumps(report))

    result = token_client._extract_frictionless_errors(html)

    assert result == [
        "locationID 'dona-001' already exists",
        "longitude must be a number",
    ]


def test_extract_frictionless_errors_includes_top_level_errors(token_client):
    """_extract_frictionless_errors() también incluye report.errors[] de nivel superior."""
    report = {"valid": False, "errors": [{"message": "top-level failure"}], "tasks": []}
    html = _table_errors_page(json.dumps(report))

    result = token_client._extract_frictionless_errors(html)

    assert result == ["top-level failure"]


def test_extract_frictionless_errors_falls_back_to_note_or_type(token_client):
    """_extract_frictionless_errors() usa note o type si falta message."""
    report = {"tasks": [{"errors": [{"type": "constraint-error", "note": "some note"}, {"type": "type-error"}]}]}
    html = _table_errors_page(json.dumps(report))

    result = token_client._extract_frictionless_errors(html)

    assert result == ["some note", "type-error"]


def test_extract_frictionless_errors_caps_at_max_errors(token_client):
    """_extract_frictionless_errors() limita el número de mensajes devueltos."""
    report = {"tasks": [{"errors": [{"message": f"error {i}"} for i in range(30)]}]}
    html = _table_errors_page(json.dumps(report))

    result = token_client._extract_frictionless_errors(html, max_errors=5)

    assert len(result) == 6  # 5 mensajes + nota de truncado
    assert result[:5] == [f"error {i}" for i in range(5)]
    assert "more errors" in result[5]


def test_extract_frictionless_errors_returns_none_when_no_report(token_client):
    """_extract_frictionless_errors() devuelve None si la página no tiene report embebido."""
    html = '<div class="alert alert-danger">Some other error</div>'

    assert token_client._extract_frictionless_errors(html) is None


def test_extract_frictionless_errors_returns_none_on_invalid_json(token_client):
    """_extract_frictionless_errors() no revienta si el JSON embebido es inválido."""
    html = _table_errors_page("{not valid json,,,}")

    assert token_client._extract_frictionless_errors(html) is None


def test_extract_frictionless_errors_returns_none_when_no_errors_present(token_client):
    """_extract_frictionless_errors() devuelve None si el report no trae errores (caso raro)."""
    html = _table_errors_page(json.dumps({"valid": True, "tasks": [{"errors": []}]}))

    assert token_client._extract_frictionless_errors(html) is None


def test_extract_html_error_text_prefers_frictionless_report(token_client):
    """_extract_html_error_text() prioriza los errores del report sobre el banner genérico."""
    report = {"tasks": [{"errors": [{"message": "locationID 'dona-001' already exists"}]}]}
    html = _table_errors_page(json.dumps(report))

    result = token_client._extract_html_error_text(html)

    assert "already exists" in result
    assert "could not be imported" not in result


def test_session_login_raises_without_credentials(token_client):
    """session_login() lanza ValueError si no hay user_name/user_password (solo token)."""
    with pytest.raises(ValueError):
        token_client.session_login()


def test_session_login_skips_if_session_cookie_present(basic_auth_client):
    """session_login() no repite el login si ya hay cookie sessionid."""
    basic_auth_client._client.cookies.set("sessionid", "already-there")
    basic_auth_client._client.get = MagicMock()
    basic_auth_client._client.post = MagicMock()

    basic_auth_client.session_login()

    basic_auth_client._client.get.assert_not_called()
    basic_auth_client._client.post.assert_not_called()


def test_session_login_performs_get_then_post(basic_auth_client):
    """session_login() hace GET (csrf) y luego POST con las credenciales."""
    basic_auth_client._client.get = MagicMock(side_effect=_fake_login_get(basic_auth_client))
    basic_auth_client._client.post = MagicMock(side_effect=_fake_login_post(basic_auth_client))

    basic_auth_client.session_login()

    basic_auth_client._client.get.assert_called_once()
    basic_auth_client._client.post.assert_called_once()
    post_kwargs = basic_auth_client._client.post.call_args.kwargs
    assert post_kwargs["data"]["login"] == "user"
    assert post_kwargs["data"]["password"] == "pass"
    assert post_kwargs["data"]["csrfmiddlewaretoken"] == "csrf-abc"
    assert basic_auth_client._client.cookies.get("sessionid") == "session-abc"


def test_session_login_get_follows_redirects(basic_auth_client):
    """session_login() sigue redirects en el GET inicial (http->https, proxy, ...).

    Regresión: la primera versión no pasaba follow_redirects=True, así que si
    el GET a /account/login/ devolvía un 30x (por ejemplo por un redirect a
    https, o un proxy delante del servidor) nunca se llegaba a renderizar el
    formulario real, y por tanto nunca se fijaba la cookie csrftoken.
    """
    basic_auth_client._client.get = MagicMock(side_effect=_fake_login_get(basic_auth_client))
    basic_auth_client._client.post = MagicMock(side_effect=_fake_login_post(basic_auth_client))

    basic_auth_client.session_login()

    get_kwargs = basic_auth_client._client.get.call_args.kwargs
    assert get_kwargs.get("follow_redirects") is True


def test_session_login_falls_back_to_html_scraped_csrf_token(basic_auth_client):
    """session_login() extrae el token del HTML si no hay cookie csrftoken."""
    login_page = MagicMock()
    login_page.text = (
        '<form><input type="hidden" name="csrfmiddlewaretoken" value="html-token"></form>'
    )
    login_page.status_code = 200
    basic_auth_client._client.get = MagicMock(return_value=login_page)

    def fake_post(url, *a, **kw):
        basic_auth_client._client.cookies.set("sessionid", "session-abc")
        resp = MagicMock()
        resp.status_code = 302
        return resp

    basic_auth_client._client.post = MagicMock(side_effect=fake_post)

    basic_auth_client.session_login()

    post_kwargs = basic_auth_client._client.post.call_args.kwargs
    assert post_kwargs["data"]["csrfmiddlewaretoken"] == "html-token"
    assert basic_auth_client._web_csrf_token == "html-token"


def test_session_login_raises_clear_error_when_no_csrf_found(basic_auth_client):
    """session_login() lanza un error explicativo si no hay cookie ni token en el HTML."""
    login_page = MagicMock()
    login_page.text = "<html><body>unexpected page</body></html>"
    login_page.status_code = 200
    login_page.url = "https://example.com/account/login/"
    basic_auth_client._client.get = MagicMock(return_value=login_page)
    basic_auth_client._client.post = MagicMock()

    with pytest.raises(err.APIError, match="CSRF token"):
        basic_auth_client.session_login()

    basic_auth_client._client.post.assert_not_called()


def test_session_login_raises_if_post_not_redirect(basic_auth_client):
    """session_login() lanza APIError si el POST no devuelve un redirect."""
    basic_auth_client._client.get = MagicMock(side_effect=_fake_login_get(basic_auth_client))
    basic_auth_client._client.post = MagicMock(
        side_effect=_fake_login_post(basic_auth_client, status_code=200, set_sessionid=False)
    )

    with pytest.raises(err.APIError):
        basic_auth_client.session_login()


def test_session_login_force_repeats_login(basic_auth_client):
    """session_login(force=True) repite el login aunque ya haya sessionid."""
    basic_auth_client._client.cookies.set("sessionid", "old-session")
    basic_auth_client._client.get = MagicMock(side_effect=_fake_login_get(basic_auth_client))
    basic_auth_client._client.post = MagicMock(side_effect=_fake_login_post(basic_auth_client))

    basic_auth_client.session_login(force=True)

    basic_auth_client._client.get.assert_called_once()
    basic_auth_client._client.post.assert_called_once()


def test_session_post_multipart_logs_in_first(basic_auth_client):
    """session_post_multipart() hace login de sesión si aún no hay sessionid."""
    basic_auth_client._client.get = MagicMock(side_effect=_fake_login_get(basic_auth_client))
    basic_auth_client._client.post = MagicMock(side_effect=_fake_login_post(basic_auth_client))

    basic_auth_client.session_post_multipart("/geomap/location/import/", data={}, files={})

    basic_auth_client._client.get.assert_called_once()


def test_session_post_multipart_sends_csrf_and_files(basic_auth_client):
    """session_post_multipart() incluye csrfmiddlewaretoken y los files/data."""
    basic_auth_client._client.cookies.set("sessionid", "existing-session")
    basic_auth_client._client.cookies.set("csrftoken", "csrf-xyz")
    basic_auth_client._client.post = MagicMock(return_value=MagicMock(status_code=302))

    files = {"csv_file": ("locations.csv", b"a,b\n1,2", "text/csv")}
    basic_auth_client.session_post_multipart(
        "/geomap/location/import/", data={"ignore_DST": False}, files=files,
    )

    call_kwargs = basic_auth_client._client.post.call_args.kwargs
    assert call_kwargs["data"]["csrfmiddlewaretoken"] == "csrf-xyz"
    assert call_kwargs["data"]["ignore_DST"] is False
    assert call_kwargs["files"] is files


def test_session_post_multipart_returns_raw_response(basic_auth_client):
    """session_post_multipart() devuelve la respuesta cruda (sin seguir redirects)."""
    basic_auth_client._client.cookies.set("sessionid", "existing-session")
    basic_auth_client._client.cookies.set("csrftoken", "csrf-xyz")
    mock_resp = MagicMock(status_code=302)
    basic_auth_client._client.post = MagicMock(return_value=mock_resp)

    result = basic_auth_client.session_post_multipart("/geomap/location/import/", data={}, files={})

    assert result is mock_resp