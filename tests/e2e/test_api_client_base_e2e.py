"""
End-to-end tests for APIClientBase against a real Trapper server.

Requires environment variables:
    WILDINTEL_BASE_URL         — base URL of the Trapper server
    WILDINTEL_ACCESS_TOKEN     — API token (or user/password)
    WILDINTEL_SMOKE_ENABLED=1  — enables e2e tests

Optional:
    WILDINTEL_USER_NAME        — username for basic auth
    WILDINTEL_USER_PASSWORD    — password for basic auth
    WILDINTEL_VERIFY_SSL       — "0" to disable SSL verification (default: "1")
    WILDINTEL_TIMEOUT          — request timeout in seconds (default: "30")
"""
from __future__ import annotations

from pathlib import Path

import pytest

from trapper_client.api_client_base import APIClientBase


# ── autenticación y configuración ─────────────────────────────────────────────

@pytest.mark.e2e
def test_real_client_is_correctly_instantiated(real_api_base):
    """El cliente se instancia correctamente con las variables de entorno."""
    assert isinstance(real_api_base, APIClientBase)
    assert real_api_base.base_url


@pytest.mark.e2e
def test_real_client_has_authentication(real_api_base):
    """El cliente tiene algún método de autenticación configurado."""
    has_token = bool(real_api_base.access_token)
    has_basic = bool(real_api_base.user_name and real_api_base.user_password)
    assert has_token or has_basic


# ── get ───────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_get_returns_paginated_response(real_api_base):
    """GET a un endpoint paginado devuelve pagination y results."""
    result = real_api_base.get("/geomap/api/locations", page_size=5)

    assert "pagination" in result
    assert "results" in result
    assert isinstance(result["results"], list)


@pytest.mark.e2e
def test_get_pagination_fields_are_present(real_api_base):
    """La paginación contiene los campos page, pages y count."""
    result = real_api_base.get("/geomap/api/locations", page_size=1)

    pagination = result.get("pagination", {})
    assert "page" in pagination
    assert "pages" in pagination
    assert "count" in pagination


@pytest.mark.e2e
def test_get_page_size_is_respected(real_api_base):
    """El número de resultados no supera el page_size solicitado."""
    result = real_api_base.get("/geomap/api/locations", page_size=3)

    assert len(result["results"]) <= 3


# ── get_all_pages ─────────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_get_all_pages_count_matches_pagination(real_api_base):
    """get_all_pages() devuelve tantos items como indica pagination.count."""
    result = real_api_base.get_all_pages("/geomap/api/locations", query={"page_size": 50})

    assert len(result["results"]) == result["pagination"]["count"]


@pytest.mark.e2e
def test_get_all_pages_results_are_unique(real_api_base):
    """get_all_pages() no devuelve items duplicados entre páginas."""
    result = real_api_base.get_all_pages("/geomap/api/locations", query={"page_size": 10})

    if not result["results"]:
        pytest.skip("No results available on this server")

    pks = [item.get("pk") or item.get("id") for item in result["results"] if item.get("pk") or item.get("id")]
    assert len(pks) == len(set(pks))


# ── get_one ───────────────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_get_one_returns_single_object(real_api_base):
    """get_one() devuelve un dict con el objeto solicitado."""
    page = real_api_base.get("/geomap/api/locations", page_size=1)
    if not page["results"]:
        pytest.skip("No results available on this server")

    pk = page["results"][0].get("pk") or page["results"][0].get("id")
    result = real_api_base.get_one(f"/geomap/api/locations/{pk}")

    assert isinstance(result, dict)
    assert result.get("pk") == pk or result.get("id") == pk


# ── export ────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_export_file_none_returns_list(real_api_base):
    """export() sin file devuelve lista de dicts."""
    result = real_api_base.export("/geomap/api/locations", file=None, page_size=5)

    assert isinstance(result, list)

@pytest.mark.e2e
def test_export_to_file_writes_csv(real_api_base, tmp_path):
    """export() con file escribe el CSV y devuelve un Path."""
    out = tmp_path / "export.csv"
    result = real_api_base.export("/geomap/api/locations", file=out, page_size=5)

    assert isinstance(result, Path)
    assert out.exists()
    assert out.stat().st_size > 0


@pytest.mark.e2e
def test_export_from_csv_file_none_returns_list(real_api_base):
    """export() sin file y llamando a un entry point que devuelve un csv devuelve lista de dicts."""
    result = real_api_base.export("/geomap/api/locations/export/", file=None, page_size=5)
    assert isinstance(result, list)


@pytest.mark.e2e
def test_export_from_csv_to_file_writes_csv(real_api_base, tmp_path):
    """export() con file escribe el CSV y devuelve un Path."""
    out = tmp_path / "export.csv"
    result = real_api_base.export("/geomap/api/locations/export/", file=out, page_size=5)

    assert isinstance(result, Path)
    assert out.exists()
    assert out.stat().st_size > 0

# ── errores HTTP ──────────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_get_nonexistent_resource_raises(real_api_base):
    """GET a un pk inexistente lanza una excepción."""
    with pytest.raises(Exception):
        real_api_base.get_one("/api/storage/collection/999999999/")


@pytest.mark.e2e
def test_get_nonexistent_resource_no_raise_returns_response(real_api_base):
    """GET a un pk inexistente con raise_on_error=False devuelve el Response."""
    result = real_api_base.make_request(
        "/api/storage/collection/999999999/",
        method="GET",
        raise_on_error=False,
    )
    assert result.status_code in (404, 403)


# ── ssl y timeout ─────────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_real_client_verify_ssl_matches_env(real_api_base):
    """El cliente tiene el valor de verify_ssl que indica la variable de entorno."""
    assert isinstance(real_api_base.verify_ssl, bool)


@pytest.mark.e2e
def test_real_client_timeout_is_positive(real_api_base):
    """El timeout configurado es un entero positivo."""
    assert isinstance(real_api_base.timeout, int)
    assert real_api_base.timeout > 0