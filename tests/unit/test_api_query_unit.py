"""
Unit tests for APIQuery.

All API calls are mocked — no real server is needed.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from trapper_client.api_query import APIQuery


# ── schemas de prueba ─────────────────────────────────────────────────────────

class ItemSchema(BaseModel):
    pk: int
    name: str


# ── helpers ───────────────────────────────────────────────────────────────────

def make_client(pages: list[dict[str, Any]]) -> MagicMock:
    """Construye un mock de cliente que devuelve páginas secuencialmente."""
    client = MagicMock()
    client.get.side_effect = pages
    return client


def single_page(results: list[dict], count: int | None = None) -> dict:
    """Construye una respuesta de una sola página."""
    return {
        "pagination": {"page": 1, "pages": 1, "page_size": len(results), "count": count or len(results)},
        "results": results,
    }


def page(results: list[dict], page_num: int, total_pages: int) -> dict:
    """Construye una respuesta de página múltiple."""
    return {
        "pagination": {"page": page_num, "pages": total_pages, "page_size": len(results), "count": total_pages * len(results)},
        "results": results,
    }


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def simple_client():
    """Cliente mock con dos resultados en una sola página."""
    return make_client([
        single_page([{"pk": 1, "name": "Alpha"}, {"pk": 2, "name": "Beta"}])
    ])


# ── iteración básica ──────────────────────────────────────────────────────────

def test_iterates_single_page(simple_client):
    """Itera correctamente una sola página y devuelve todos los items."""
    query = APIQuery(simple_client, "/api/items/")
    items = list(query)

    assert len(items) == 2


def test_returns_dicts_without_schema(simple_client):
    """Sin schema, devuelve los items como dicts."""
    query = APIQuery(simple_client, "/api/items/")
    items = list(query)

    assert all(isinstance(item, dict) for item in items)
    assert items[0]["pk"] == 1


def test_returns_models_with_schema(simple_client):
    """Con schema, devuelve instancias del modelo Pydantic."""
    query = APIQuery(simple_client, "/api/items/", schema=ItemSchema)
    items = list(query)

    assert all(isinstance(item, ItemSchema) for item in items)
    assert items[0].pk == 1
    assert items[0].name == "Alpha"


def test_iterates_multiple_pages():
    """Itera correctamente varias páginas concatenando los items."""
    client = make_client([
        page([{"pk": 1, "name": "A"}, {"pk": 2, "name": "B"}], page_num=1, total_pages=2),
        page([{"pk": 3, "name": "C"}, {"pk": 4, "name": "D"}], page_num=2, total_pages=2),
    ])

    items = list(APIQuery(client, "/api/items/"))

    assert len(items) == 4
    assert items[-1]["pk"] == 4


def test_calls_client_once_per_page():
    """Se llama al cliente exactamente una vez por página."""
    client = make_client([
        page([{"pk": 1, "name": "A"}], page_num=1, total_pages=3),
        page([{"pk": 2, "name": "B"}], page_num=2, total_pages=3),
        page([{"pk": 3, "name": "C"}], page_num=3, total_pages=3),
    ])

    list(APIQuery(client, "/api/items/"))

    assert client.get.call_count == 3


def test_passes_page_size_to_client():
    """Se envía el page_size correcto en cada petición."""
    client = make_client([single_page([{"pk": 1, "name": "A"}])])

    list(APIQuery(client, "/api/items/", page_size=25))

    call_params = client.get.call_args_list[0][0][1]
    assert call_params["page_size"] == 25


def test_passes_query_params_to_client():
    """Los parámetros de query base se envían al cliente."""
    client = make_client([single_page([{"pk": 1, "name": "A"}])])

    list(APIQuery(client, "/api/items/", query={"search": "test", "owner": True}))

    call_params = client.get.call_args_list[0][0][1]
    assert call_params["search"] == "test"
    assert call_params["owner"] is True


# ── página vacía ──────────────────────────────────────────────────────────────

def test_empty_results_raises_stop_iteration():
    """Una página vacía detiene la iteración inmediatamente."""
    client = make_client([single_page([])])

    items = list(APIQuery(client, "/api/items/"))

    assert items == []


# ── filter_fn ─────────────────────────────────────────────────────────────────

def test_filter_fn_filters_items(simple_client):
    """filter_fn filtra items del lado del cliente."""
    query = APIQuery(
        simple_client,
        "/api/items/",
        filter_fn=lambda item: item["pk"] == 1,
    )
    items = list(query)

    assert len(items) == 1
    assert items[0]["pk"] == 1


def test_filter_fn_works_with_schema():
    """filter_fn recibe instancias del modelo cuando se usa schema."""
    client = make_client([
        single_page([{"pk": 1, "name": "Alpha"}, {"pk": 2, "name": "Beta"}])
    ])
    query = APIQuery(
        client,
        "/api/items/",
        schema=ItemSchema,
        filter_fn=lambda item: item.name == "Beta",
    )
    items = list(query)

    assert len(items) == 1
    assert items[0].name == "Beta"


def test_filter_fn_all_filtered_returns_empty(simple_client):
    """Si filter_fn filtra todos los items, devuelve lista vacía."""
    query = APIQuery(simple_client, "/api/items/", filter_fn=lambda _: False)
    items = list(query)

    assert items == []


# ── validate=False ────────────────────────────────────────────────────────────

def test_validate_false_constructs_model_without_validation():
    """validate=False construye modelos sin ejecutar validación Pydantic."""
    client = make_client([single_page([{"pk": 1, "name": "Alpha"}])])

    query = APIQuery(client, "/api/items/", schema=ItemSchema, validate=False)
    items = list(query)

    assert isinstance(items[0], ItemSchema)


# ── resolución de placeholders ────────────────────────────────────────────────

def test_resolves_endpoint_placeholders():
    """Los placeholders {key} del endpoint se sustituyen con valores del query."""
    client = make_client([single_page([{"pk": 1, "name": "A"}])])

    list(APIQuery(client, "/api/projects/{project_pk}/items/", query={"project_pk": 42}))

    called_endpoint = client.get.call_args_list[0][0][0]
    assert called_endpoint == "/api/projects/42/items/"


def test_placeholder_value_removed_from_query_params():
    """El valor usado para resolver un placeholder no se envía como query param."""
    client = make_client([single_page([{"pk": 1, "name": "A"}])])

    list(APIQuery(client, "/api/projects/{project_pk}/items/", query={"project_pk": 42}))

    call_params = client.get.call_args_list[0][0][1]
    assert "project_pk" not in call_params


# ── __iter__ ──────────────────────────────────────────────────────────────────

def test_returns_self_on_iter(simple_client):
    """__iter__() devuelve la propia instancia."""
    query = APIQuery(simple_client, "/api/items/")
    assert iter(query) is query


# ── exhausted ─────────────────────────────────────────────────────────────────

def test_exhausted_after_full_iteration(simple_client):
    """_exhausted es True después de iterar todos los items."""
    query = APIQuery(simple_client, "/api/items/")
    list(query)

    assert query._exhausted is True


def test_raises_stop_iteration_when_exhausted(simple_client):
    """__next__() lanza StopIteration si el iterador ya está exhausto."""
    query = APIQuery(simple_client, "/api/items/")
    list(query)

    with pytest.raises(StopIteration):
        next(query)


# ── close ─────────────────────────────────────────────────────────────────────

def test_close_marks_iterator_as_exhausted(simple_client):
    """close() marca el iterador como exhausto."""
    query = APIQuery(simple_client, "/api/items/")
    query.close()

    assert query._exhausted is True


def test_close_clears_internal_buffers(simple_client):
    """close() vacía los buffers internos."""
    query = APIQuery(simple_client, "/api/items/")
    next(query)  # carga la primera página
    query.close()

    assert query._last_results == []
    assert query._last_index == 0


def test_close_raises_stop_iteration_on_next(simple_client):
    """Después de close(), __next__() lanza StopIteration."""
    query = APIQuery(simple_client, "/api/items/")
    query.close()

    with pytest.raises(StopIteration):
        next(query)


# ── context manager ───────────────────────────────────────────────────────────

def test_context_manager_yields_self(simple_client):
    """El context manager devuelve la propia instancia de APIQuery."""
    query = APIQuery(simple_client, "/api/items/")
    with query as q:
        assert q is query


def test_context_manager_exhausts_on_exit(simple_client):
    """Al salir del context manager el iterador queda exhausto."""
    query = APIQuery(simple_client, "/api/items/")
    with query:
        pass

    assert query._exhausted is True


def test_context_manager_iterates_correctly(simple_client):
    """Se puede iterar dentro del context manager."""
    items = []
    with APIQuery(simple_client, "/api/items/") as query:
        for item in query:
            items.append(item)

    assert len(items) == 2


def test_context_manager_does_not_suppress_exceptions():
    """Las excepciones dentro del context manager no se suprimen."""
    client = make_client([single_page([{"pk": 1, "name": "A"}])])

    with pytest.raises(ValueError):
        with APIQuery(client, "/api/items/"):
            raise ValueError("test error")