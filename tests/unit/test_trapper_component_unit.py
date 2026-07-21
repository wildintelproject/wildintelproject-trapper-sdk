"""
Unit tests for TrapperComponent.

All API calls are mocked — no real server is needed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from trapper_client.components.base import TrapperComponent
from trapper_client.api_query import APIQuery
from trapper_client.schemas import PaginatedResult, Pagination


# ── schemas de prueba ─────────────────────────────────────────────────────────

class LocationSchema(BaseModel):
    pk: int
    name: str | None = None


class LocationExportSchema(BaseModel):
    pk: int
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None


# ── componente de prueba ──────────────────────────────────────────────────────

class LocationsComponent(TrapperComponent[LocationSchema]):
    endpoint = "/geomap/api/locations/"
    schema = LocationSchema
    export_schema = LocationExportSchema
    export_endpoint = "/geomap/api/locations/export/"


# ── helpers ───────────────────────────────────────────────────────────────────

def make_client() -> MagicMock:
    """Construye un mock de APIClientBase."""
    return MagicMock()


def paginated_response(
    results: list[dict],
    page: int = 1,
    pages: int = 1,
) -> dict:
    """Construye una respuesta paginada."""
    return {
        "pagination": {
            "page": page,
            "pages": pages,
            "page_size": len(results),
            "count": len(results),
        },
        "results": results,
    }


LOCATION_1 = {"pk": 1, "name": "Location A"}
LOCATION_2 = {"pk": 2, "name": "Location B"}
LOCATION_EXPORT_1 = {"pk": 1, "name": "Location A", "latitude": 37.1, "longitude": -6.9}


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return make_client()


@pytest.fixture
def component(client):
    return LocationsComponent(client)


# ── __init__ / __repr__ ───────────────────────────────────────────────────────

def test_component_stores_client(client):
    """El componente almacena el cliente correctamente."""
    comp = LocationsComponent(client)
    assert comp.client is client


def test_repr_contains_endpoint(component):
    """__repr__() incluye el endpoint configurado."""
    assert "/geomap/api/locations/" in repr(component)


def test_repr_contains_class_name(component):
    """__repr__() incluye el nombre de la clase."""
    assert "LocationsComponent" in repr(component)


# ── _merge_query ──────────────────────────────────────────────────────────────

def test_merge_query_combines_dicts(component):
    """_merge_query() combina query base y kwargs."""
    result = component._merge_query({"page": 1}, {"page_size": 25})
    assert result == {"page": 1, "page_size": 25}


def test_merge_query_kwargs_override_query(component):
    """_merge_query() deja que kwargs sobreescriban claves de query."""
    result = component._merge_query({"page_size": 10}, {"page_size": 50})
    assert result["page_size"] == 50


def test_merge_query_returns_empty_dict_when_both_empty(component):
    """_merge_query() devuelve dict vacío cuando no hay parámetros."""
    result = component._merge_query(None, {})
    assert result == {}


def test_merge_query_always_returns_dict(component):
    """_merge_query() siempre devuelve dict, nunca None."""
    result = component._merge_query(None, {})
    assert isinstance(result, dict)


# ── _to_model ─────────────────────────────────────────────────────────────────

def test_to_model_validates_dict(component):
    """_to_model() parsea un dict con validate=True."""
    result = component._to_model({"pk": 1, "name": "A"}, validate=True)
    assert isinstance(result, LocationSchema)
    assert result.pk == 1


def test_to_model_constructs_without_validation(component):
    """_to_model() construye el modelo sin validación cuando validate=False."""
    result = component._to_model({"pk": 1, "name": "A"}, validate=False)
    assert isinstance(result, LocationSchema)


def test_to_model_returns_instance_unchanged(component):
    """_to_model() devuelve la instancia tal cual si ya es del tipo correcto."""
    instance = LocationSchema(pk=1, name="A")
    result = component._to_model(instance, validate=True)
    assert result is instance


def test_to_model_uses_overwrite_schema(component):
    """_to_model() usa el schema indicado en lugar de self.schema."""
    result = component._to_model(
        {"pk": 1, "name": "A", "latitude": 37.1, "longitude": -6.9},
        validate=True,
        schema=LocationExportSchema,
    )
    assert isinstance(result, LocationExportSchema)
    assert result.latitude == 37.1


# ── _to_paginated ─────────────────────────────────────────────────────────────

def test_to_paginated_returns_paginated_result(component):
    """_to_paginated() devuelve PaginatedResult con items tipados."""
    data = paginated_response([LOCATION_1, LOCATION_2])
    result = component._to_paginated(data, validate=True)

    assert isinstance(result, PaginatedResult)
    assert len(result.results) == 2
    assert all(isinstance(item, LocationSchema) for item in result.results)


def test_to_paginated_fills_missing_pagination_fields(component):
    """_to_paginated() usa valores por defecto si faltan campos de paginación."""
    data = {"results": [LOCATION_1]}
    result = component._to_paginated(data, validate=True)

    assert result.pagination.page == 1
    assert result.pagination.pages == 1
    assert result.pagination.count == 1


def test_to_paginated_empty_results(component):
    """_to_paginated() maneja correctamente una lista de resultados vacía."""
    data = paginated_response([])
    result = component._to_paginated(data, validate=True)

    assert result.results == []
    assert result.pagination.count == 0


def test_to_paginated_uses_overwrite_schema(component):
    """_to_paginated() usa el schema indicado para parsear los items."""
    data = paginated_response([LOCATION_EXPORT_1])
    result = component._to_paginated(data, validate=True, schema=LocationExportSchema)

    assert isinstance(result.results[0], LocationExportSchema)
    assert result.results[0].latitude == 37.1


# ── get ───────────────────────────────────────────────────────────────────────

def test_get_returns_paginated_result(component, client):
    """get() devuelve PaginatedResult con items tipados."""
    client.get.return_value = paginated_response([LOCATION_1, LOCATION_2])

    result = component.get(page_size=10)

    assert isinstance(result, PaginatedResult)
    assert len(result.results) == 2
    assert isinstance(result.results[0], LocationSchema)


def test_get_sends_page_and_page_size(component, client):
    """get() envía los parámetros page y page_size al cliente."""
    client.get.return_value = paginated_response([LOCATION_1])

    component.get(page=2, page_size=25)

    call_params = client.get.call_args[1]["query"]
    assert call_params["page"] == 2
    assert call_params["page_size"] == 25


def test_get_uses_component_endpoint(component, client):
    """get() usa el endpoint del componente."""
    client.get.return_value = paginated_response([])

    component.get()

    assert client.get.call_args[0][0] == "/geomap/api/locations/"


def test_get_uses_overwrite_endpoint(component, client):
    """get() usa overwrite_endpoint cuando se especifica."""
    client.get.return_value = paginated_response([])

    component.get(overwrite_endpoint="/other/endpoint/")

    assert client.get.call_args[0][0] == "/other/endpoint/"


def test_get_uses_overwrite_schema(component, client):
    """get() usa overwrite_schema para parsear los items."""
    client.get.return_value = paginated_response([LOCATION_EXPORT_1])

    result = component.get(overwrite_schema=LocationExportSchema)

    assert isinstance(result.results[0], LocationExportSchema)


def test_get_passes_extra_kwargs_as_query_params(component, client):
    """get() pasa kwargs adicionales como parámetros de consulta."""
    client.get.return_value = paginated_response([])

    component.get(search="test", owner=True)

    call_params = client.get.call_args[1]["query"]
    assert call_params["search"] == "test"
    assert call_params["owner"] is True


def test_get_validate_false_constructs_without_validation(component, client):
    """get() con validate=False construye modelos sin validación."""
    client.get.return_value = paginated_response([LOCATION_1])

    result = component.get(validate=False)

    assert isinstance(result.results[0], LocationSchema)


# ── get_all ───────────────────────────────────────────────────────────────────

def test_get_all_returns_paginated_result(component, client):
    """get_all() devuelve PaginatedResult con todos los items."""
    client.get_all.return_value = paginated_response([LOCATION_1, LOCATION_2])

    result = component.get_all()

    assert isinstance(result, PaginatedResult)
    assert len(result.results) == 2


def test_get_all_sends_page_size(component, client):
    """get_all() envía el page_size al cliente."""
    client.get_all.return_value = paginated_response([])

    component.get_all(page_size=100)

    call_params = client.get_all.call_args[1]["query"]
    assert call_params["page_size"] == 100


def test_get_all_uses_overwrite_endpoint(component, client):
    """get_all() usa overwrite_endpoint cuando se especifica."""
    client.get_all.return_value = paginated_response([])

    component.get_all(overwrite_endpoint="/other/endpoint/")

    assert client.get_all.call_args[0][0] == "/other/endpoint/"


def test_get_all_uses_overwrite_schema(component, client):
    """get_all() usa overwrite_schema para parsear los items."""
    client.get_all.return_value = paginated_response([LOCATION_EXPORT_1])

    result = component.get_all(overwrite_schema=LocationExportSchema)

    assert isinstance(result.results[0], LocationExportSchema)


# ── where ─────────────────────────────────────────────────────────────────────

def test_where_returns_api_query(component):
    """where() devuelve un APIQuery sin ejecutar peticiones."""
    result = component.where(page_size=10)
    assert isinstance(result, APIQuery)


def test_where_uses_component_endpoint(component):
    """where() configura el endpoint del componente en el APIQuery."""
    query = component.where()
    assert query.endpoint == "/geomap/api/locations/"


def test_where_uses_overwrite_endpoint(component):
    """where() usa overwrite_endpoint cuando se especifica."""
    query = component.where(overwrite_endpoint="/other/endpoint/")
    assert query.endpoint == "/other/endpoint/"


def test_where_uses_overwrite_schema(component):
    """where() usa overwrite_schema en el APIQuery."""
    query = component.where(overwrite_schema=LocationExportSchema)
    assert query.schema is LocationExportSchema


def test_where_passes_filter_fn(component):
    """where() pasa filter_fn al APIQuery."""
    fn = lambda item: item.pk == 1
    query = component.where(filter_fn=fn)
    assert query.filter_fn is fn


def test_where_passes_page_size(component):
    """where() pasa page_size al APIQuery."""
    query = component.where(page_size=25)
    assert query._page_size == 25


def test_where_passes_query_params(component):
    """where() pasa los parámetros de query al APIQuery."""
    query = component.where(search="test", owner=True)
    assert query.query["search"] == "test"
    assert query.query["owner"] is True


# ── find ──────────────────────────────────────────────────────────────────────

def test_find_returns_model(component, client):
    """find() devuelve una instancia del schema."""
    client.get_one.return_value = LOCATION_1

    result = component.find(1)

    assert isinstance(result, LocationSchema)
    assert result.pk == 1


def test_find_calls_correct_endpoint(component, client):
    """find() construye el endpoint con el pk correctamente."""
    client.get_one.return_value = LOCATION_1

    component.find(42)

    called_endpoint = client.get_one.call_args[0][0]
    assert called_endpoint == "/geomap/api/locations/42"


def test_find_uses_overwrite_endpoint(component, client):
    """find() usa overwrite_endpoint cuando se especifica."""
    client.get_one.return_value = LOCATION_1

    component.find(1, overwrite_endpoint="/other/endpoint/")

    called_endpoint = client.get_one.call_args[0][0]
    assert "/other/endpoint/" in called_endpoint


def test_find_uses_overwrite_schema(component, client):
    """find() usa overwrite_schema para parsear el resultado."""
    client.get_one.return_value = LOCATION_EXPORT_1

    result = component.find(1, overwrite_schema=LocationExportSchema)

    assert isinstance(result, LocationExportSchema)
    assert result.latitude == 37.1


def test_find_validate_false_constructs_without_validation(component, client):
    """find() con validate=False construye el modelo sin validación."""
    client.get_one.return_value = LOCATION_1

    result = component.find(1, validate=False)

    assert isinstance(result, LocationSchema)


def test_find_handles_paginated_response(component, client):
    """find() extrae el primer resultado si el servidor devuelve paginación."""
    client.get_one.return_value = paginated_response([LOCATION_1])

    result = component.find(1)

    assert isinstance(result, LocationSchema)
    assert result.pk == 1


def test_find_raises_if_paginated_response_is_empty(component, client):
    """find() lanza KeyError si la respuesta paginada no tiene resultados."""
    client.get_one.return_value = paginated_response([])

    with pytest.raises(KeyError):
        component.find(999)


# ── export ────────────────────────────────────────────────────────────────────

def test_export_returns_list_of_models_when_file_is_none(component, client):
    """export() devuelve lista de modelos cuando file=None."""
    client.get_all.return_value = paginated_response([LOCATION_EXPORT_1])

    result = component.export(file=None)

    assert isinstance(result, list)
    assert isinstance(result[0], LocationExportSchema)


def test_export_uses_export_schema_by_default(component, client):
    """export() usa export_schema del componente por defecto."""
    client.get_all.return_value = paginated_response([LOCATION_EXPORT_1])

    result = component.export(file=None)

    assert isinstance(result[0], LocationExportSchema)


def test_export_uses_export_endpoint_by_default(component, client):
    """export() usa export_endpoint del componente por defecto."""
    client.get_all.return_value = paginated_response([])

    component.export(file=None)

    assert client.get_all.call_args[0][0] == "/geomap/api/locations/export/"


def test_export_uses_overwrite_endpoint(component, client):
    """export() usa overwrite_endpoint cuando se especifica."""
    client.get_all.return_value = paginated_response([])

    component.export(file=None, overwrite_endpoint="/other/export/")

    assert client.get_all.call_args[0][0] == "/other/export/"


def test_export_uses_overwrite_schema(component, client):
    """export() usa overwrite_schema cuando se especifica."""
    client.get_all.return_value = paginated_response([LOCATION_1])

    result = component.export(file=None, overwrite_schema=LocationSchema)

    assert isinstance(result[0], LocationSchema)


def test_export_writes_csv_when_file_provided(component, client, tmp_path):
    """export() escribe CSV y devuelve Path cuando se indica file."""
    client.get_all.return_value = paginated_response([LOCATION_EXPORT_1])
    client._select_file.return_value = tmp_path / "locations.csv"
    client._write_csv = MagicMock()

    result = component.export(file=tmp_path / "locations.csv")

    assert isinstance(result, Path)
    client._write_csv.assert_called_once()


def test_export_validate_false_constructs_without_validation(component, client):
    """export() con validate=False construye modelos sin validación."""
    client.get_all.return_value = paginated_response([LOCATION_EXPORT_1])

    result = component.export(file=None, validate=False)

    assert isinstance(result, list)
    assert isinstance(result[0], LocationExportSchema)