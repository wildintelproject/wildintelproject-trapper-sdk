"""
End-to-end tests for TrapperComponent against a real Trapper server
using /geomap/api/locations as the test endpoint.

Requires environment variables:
    WILDINTEL_BASE_URL         — base URL of the Trapper server
    WILDINTEL_ACCESS_TOKEN     — API token (or user/password)
    WILDINTEL_SMOKE_ENABLED=1  — enables e2e tests

Optional:
    WILDINTEL_LOCATION_PK      — pk of an existing location (for find tests)
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import BaseModel

from trapper_client.components.base import TrapperComponent
from trapper_client.api_query import APIQuery
from trapper_client.schemas import PaginatedResult

from trapper_client.schemas import Location, LocationExport
# ── componente real ───────────────────────────────────────────────────────────

class LocationsComponent(TrapperComponent[Location]):
    endpoint = "/geomap/api/locations"
    schema = Location
    export_schema = LocationExport
    export_endpoint = "/geomap/api/locations/export/"


# ── fixture de componente ─────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def locations(real_api_base):
    """Componente de locations conectado al servidor real."""
    return LocationsComponent(real_api_base)


# ── get ───────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_get_returns_paginated_result(locations):
    """get() devuelve PaginatedResult con la primera página."""
    result = locations.get(page_size=5)

    assert isinstance(result, PaginatedResult)
    assert isinstance(result.results, list)
    assert result.pagination.page == 1
    assert result.pagination.page_size == 5


@pytest.mark.e2e
def test_get_returns_location_instances(locations):
    """get() devuelve instancias de LocationSchema."""
    result = locations.get(page_size=5)

    if not result.results:
        pytest.skip("No locations available on this server")

    for loc in result.results:
        assert isinstance(loc, Location)
        assert isinstance(loc.pk, int)


@pytest.mark.e2e
def test_get_validate_false_returns_models_without_validation(locations):
    """get() con validate=False devuelve modelos construidos sin validación."""
    result = locations.get(page_size=5, validate=False)

    if not result.results:
        pytest.skip("No locations available on this server")

    assert all(isinstance(loc, Location) for loc in result.results)


@pytest.mark.e2e
def test_get_page_size_is_respected(locations):
    """El número de resultados no supera el page_size solicitado."""
    result = locations.get(page_size=3)

    assert len(result.results) <= 3


@pytest.mark.e2e
def test_get_with_overwrite_schema_returns_export_models(locations):
    """get() con overwrite_schema devuelve instancias del schema indicado."""
    result = locations.get(page_size=5, overwrite_schema=LocationExport)

    if not result.results:
        pytest.skip("No locations available on this server")

    assert all(isinstance(loc, LocationExport) for loc in result.results)


# ── get_all ───────────────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_get_all_count_matches_pagination(locations):
    """get_all() devuelve tantos items como indica pagination.count."""
    result = locations.get_all(page_size=50)

    assert len(result.results) == result.pagination.count


@pytest.mark.e2e
def test_get_all_returns_location_instances(locations):
    """get_all() devuelve instancias de LocationSchema."""
    result = locations.get_all(page_size=50)

    for loc in result.results:
        assert isinstance(loc, Location)
        assert isinstance(loc.pk, int)


@pytest.mark.e2e
def test_get_all_no_duplicate_pks(locations):
    """get_all() no devuelve items duplicados entre páginas."""
    result = locations.get_all(page_size=10)

    if not result.results:
        pytest.skip("No locations available on this server")

    pks = [loc.pk for loc in result.results]
    assert len(pks) == len(set(pks))


# ── where ─────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_where_returns_api_query(locations):
    """where() devuelve un APIQuery sin ejecutar peticiones."""
    query = locations.where(page_size=5)
    assert isinstance(query, APIQuery)


@pytest.mark.e2e
def test_where_iterates_and_returns_location_instances(locations):
    """Iterar where() devuelve instancias de LocationSchema."""
    items = []
    for loc in locations.where(page_size=10):
        items.append(loc)
        if len(items) >= 5:
            break

    if not items:
        pytest.skip("No locations available on this server")

    for loc in items:
        assert isinstance(loc, Location)
        assert isinstance(loc.pk, int)


@pytest.mark.e2e
def test_where_context_manager_exhausts_on_exit(locations):
    """where() funciona correctamente como context manager."""
    with locations.where(page_size=5) as query:
        first = next(query, None)

    assert query._exhausted is True

    if first is None:
        pytest.skip("No locations available on this server")

    assert isinstance(first, Location)


@pytest.mark.e2e
def test_where_filter_fn_filters_results(locations):
    """where() con filter_fn filtra correctamente los resultados."""
    all_items = list(locations.where(page_size=50))

    if not all_items:
        pytest.skip("No locations available on this server")

    target_pk = all_items[0].pk
    filtered = list(locations.where(
        page_size=50,
        filter_fn=lambda loc: loc.pk == target_pk,
    ))

    assert len(filtered) == 1
    assert filtered[0].pk == target_pk


@pytest.mark.e2e
def test_where_with_overwrite_schema(locations):
    """where() con overwrite_schema devuelve instancias del schema indicado."""
    items = []
    for loc in locations.where(page_size=5, overwrite_schema=LocationExport):
        items.append(loc)
        if len(items) >= 3:
            break

    if not items:
        pytest.skip("No locations available on this server")

    assert all(isinstance(loc, LocationExport) for loc in items)


# ── find ──────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_find_returns_location_instance(locations):
    """find(pk) devuelve la LocationSchema correcta."""
    pk = os.getenv("WILDINTEL_LOCATION_PK", "").strip()
    if not pk:
        pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

    result = locations.find(int(pk))

    assert isinstance(result, Location)
    assert result.pk == int(pk)


@pytest.mark.e2e
def test_find_validate_false_returns_model_without_validation(locations):
    """find() con validate=False devuelve modelo construido sin validación."""
    pk = os.getenv("WILDINTEL_LOCATION_PK", "").strip()
    if not pk:
        pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

    result = locations.find(int(pk), validate=False)

    assert isinstance(result, Location)


@pytest.mark.e2e
def test_find_with_overwrite_schema(locations):
    """find() con overwrite_schema devuelve instancia del schema indicado."""
    pk = os.getenv("WILDINTEL_LOCATION_PK", "").strip()
    if not pk:
        pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

    result = locations.find(int(pk), overwrite_schema=LocationExport)

    assert isinstance(result, LocationExport)


@pytest.mark.e2e
def test_find_nonexistent_pk_raises(locations):
    """find() lanza excepción para un pk que no existe."""
    with pytest.raises(Exception):
        locations.find(999999999)


# ── export ────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_export_file_none_returns_list_of_models(locations):
    """export() sin file devuelve lista de instancias de LocationExportSchema."""
    result = locations.export(file=None)

    assert isinstance(result, list)
    if result:
        assert isinstance(result[0], LocationExport)


@pytest.mark.e2e
def test_export_to_csv_writes_file(locations, tmp_path):
    """export() escribe CSV y devuelve Path."""
    out = tmp_path / "locations.csv"
    result = locations.export(file=out)

    assert isinstance(result, Path)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert len(content) > 0
    assert "pk" in content


@pytest.mark.e2e
def test_export_csv_row_count_matches_get_all(locations, tmp_path):
    """El CSV exportado tiene tantas filas de datos como indica get_all."""
    all_result = locations.get_all(page_size=50)
    expected = len(all_result.results)

    if expected == 0:
        pytest.skip("No locations available on this server")

    out = tmp_path / "locations.csv"
    locations.export(file=out)

    lines = out.read_text(encoding="utf-8").strip().splitlines()
    data_rows = len(lines) - 1  # descontar cabecera
    assert data_rows == expected


@pytest.mark.e2e
def test_export_with_overwrite_schema_returns_correct_type(locations):
    """export() con overwrite_schema devuelve instancias del schema indicado."""
    result = locations.export(file=None, overwrite_schema=LocationExport)

    assert isinstance(result, list)
    if result:
        assert isinstance(result[0], LocationExport)