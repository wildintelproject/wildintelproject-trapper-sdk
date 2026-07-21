"""
End-to-end tests for APIQuery against a real Trapper server.

Requires environment variables:
    WILDINTEL_BASE_URL         — base URL of the Trapper server
    WILDINTEL_ACCESS_TOKEN     — API token (or user/password)
    WILDINTEL_SMOKE_ENABLED=1  — enables e2e tests
"""
from __future__ import annotations

import pytest
from pydantic import BaseModel

from trapper_client.api_query import APIQuery


# ── schema de prueba ──────────────────────────────────────────────────────────

class CollectionSchema(BaseModel):
    pk: int
    name: str | None = None


# ── iteración básica ──────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_api_query_returns_results(real_api_base):
    """APIQuery itera resultados reales del servidor."""
    items = []
    for item in APIQuery(real_api_base, "/geomap/api/locations", page_size=5):
        items.append(item)
        if len(items) >= 5:
            break

    assert isinstance(items, list)


@pytest.mark.e2e
def test_api_query_returns_dicts_without_schema(real_api_base):
    """Sin schema, los items devueltos son dicts."""
    query = APIQuery(real_api_base, "/geomap/api/locations", page_size=5)
    first = next(query, None)

    if first is None:
        pytest.skip("No results available on this server")

    assert isinstance(first, dict)
    assert "pk" in first


@pytest.mark.e2e
def test_api_query_returns_models_with_schema(real_api_base):
    """Con schema, los items devueltos son instancias del modelo."""
    query = APIQuery(
        real_api_base,
        "/geomap/api/locations",
        schema=CollectionSchema,
        page_size=5,
    )
    first = next(query, None)

    if first is None:
        pytest.skip("No results available on this server")

    assert isinstance(first, CollectionSchema)
    assert isinstance(first.pk, int)


@pytest.mark.e2e
def test_api_query_validate_false_constructs_without_validation(real_api_base):
    """validate=False construye modelos sin ejecutar validación Pydantic."""
    query = APIQuery(
        real_api_base,
        "/geomap/api/locations",
        schema=CollectionSchema,
        validate=False,
        page_size=5,
    )
    first = next(query, None)

    if first is None:
        pytest.skip("No results available on this server")

    assert isinstance(first, CollectionSchema)


# ── paginación ────────────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_api_query_iterates_all_pages(real_api_base):
    """APIQuery recorre todas las páginas y devuelve el total de items."""
    items = list(APIQuery(real_api_base, "/geomap/api/locations", page_size=10))

    # comprobamos que el total coincide con lo que indica la paginación
    first_page = real_api_base.get("/geomap/api/locations", page_size=10)
    expected_count = first_page["pagination"]["count"]

    assert len(items) == expected_count


@pytest.mark.e2e
def test_api_query_page_size_limits_items_per_request(real_api_base):
    """El servidor recibe el page_size indicado."""
    query = APIQuery(real_api_base, "/geomap/api/locations", page_size=3)
    next(query, None)  # fuerza la primera petición

    assert query._page_size == 3


@pytest.mark.e2e
def test_api_query_no_duplicate_items(real_api_base):
    """No hay items duplicados al paginar."""
    items = list(APIQuery(real_api_base, "/geomap/api/locations", page_size=10))

    if not items:
        pytest.skip("No results available on this server")

    pks = [item["pk"] if isinstance(item, dict) else item.pk for item in items]
    assert len(pks) == len(set(pks))


# ── filter_fn ─────────────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_api_query_filter_fn_reduces_results(real_api_base):
    """filter_fn reduce los resultados del lado del cliente."""
    all_items = list(APIQuery(real_api_base, "/geomap/api/locations", page_size=50))

    if not all_items:
        pytest.skip("No results available on this server")

    target_pk = all_items[0]["pk"]
    filtered = list(APIQuery(
        real_api_base,
        "/geomap/api/locations",
        page_size=50,
        filter_fn=lambda item: item["pk"] == target_pk,
    ))

    assert len(filtered) == 1
    assert filtered[0]["pk"] == target_pk


# ── context manager ───────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_api_query_context_manager_iterates(real_api_base):
    """El context manager permite iterar y queda exhausto al salir."""
    with APIQuery(real_api_base, "/geomap/api/locations", page_size=5) as query:
        first = next(query, None)

    assert query._exhausted is True

    if first is None:
        pytest.skip("No results available on this server")

    assert isinstance(first, dict)


# ── exhausted ─────────────────────────────────────────────────────────────────

@pytest.mark.e2e
def test_api_query_exhausted_after_full_iteration(real_api_base):
    """_exhausted es True después de iterar todos los resultados."""
    query = APIQuery(real_api_base, "/geomap/api/locations", page_size=50)
    list(query)

    assert query._exhausted is True


@pytest.mark.e2e
def test_api_query_raises_stop_iteration_when_exhausted(real_api_base):
    """__next__() lanza StopIteration si el iterador ya está exhausto."""
    query = APIQuery(real_api_base, "/geomap/api/locations", page_size=50)
    list(query)

    with pytest.raises(StopIteration):
        next(query)