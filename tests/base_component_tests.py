"""
Base test classes for TrapperComponent subclasses.

Usage — unit tests:
    from tests.base import ComponentUnitTestBase
    from trapper_client.components.locations import LocationsComponent
    from trapper_client.schemas import Location, LocationExport

    class TestLocationsComponent(ComponentUnitTestBase):
        component_class = LocationsComponent
        schema = Location
        export_schema = LocationExport
        valid_item = {"pk": 1, "name": "Location A"}
        valid_export_item = {"_id": 1, "locationID": "dona_001", "latitude": 37.1, "longitude": -6.9}
        find_pk = 1

Usage — e2e tests:
    from tests.base import ComponentE2ETestBase
    from trapper_client.components.locations import LocationsComponent
    from trapper_client.schemas import Location, LocationExport

    class TestLocationsComponentE2E(ComponentE2ETestBase):
        component_class = LocationsComponent
        schema = Location
        export_schema = LocationExport
        env_pk_var = "WILDINTEL_LOCATION_PK"
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from trapper_client.api_query import APIQuery
from trapper_client.schemas import PaginatedResult


# ── helpers compartidos ───────────────────────────────────────────────────────

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


def make_mock_client() -> MagicMock:
    """Construye un mock de APIClientBase."""
    return MagicMock()


# ── clase base unit tests ─────────────────────────────────────────────────────

class ComponentUnitTestBase:
    """
    Base class for TrapperComponent unit tests.

    Subclasses must define:
        component_class: The TrapperComponent subclass to test.
        schema: The main Pydantic schema class.
        export_schema: The export Pydantic schema class.
        valid_item: A dict representing a valid item from the API.
        valid_export_item: A dict representing a valid export item from the API.
        find_pk: A pk value to use in find() tests.
    """

    component_class: type
    schema: type[BaseModel]
    export_schema: type[BaseModel]
    valid_item: dict[str, Any]
    valid_export_item: dict[str, Any]
    find_pk: int | str = 1

    @pytest.fixture
    def client(self):
        return make_mock_client()

    @pytest.fixture
    def component(self, client):
        return self.component_class(client)

    # ── __repr__ ──────────────────────────────────────────────────────────────

    def test_repr_contains_class_name(self, component):
        """__repr__() incluye el nombre de la clase."""
        assert self.component_class.__name__ in repr(component)

    def test_repr_contains_endpoint(self, component):
        """__repr__() incluye el endpoint configurado."""
        assert component.endpoint in repr(component)

    # ── get ───────────────────────────────────────────────────────────────────

    def test_get_returns_paginated_result(self, component, client):
        """get() devuelve PaginatedResult con items tipados."""
        client.get.return_value = paginated_response([self.valid_item])

        result = component.get(page_size=10)

        assert isinstance(result, PaginatedResult)
        assert len(result.results) == 1
        assert isinstance(result.results[0], self.schema)

    def test_get_sends_page_and_page_size(self, component, client):
        """get() envía page y page_size al cliente."""
        client.get.return_value = paginated_response([])

        component.get(page=2, page_size=25)

        call_params = client.get.call_args[1]["query"]
        assert call_params["page"] == 2
        assert call_params["page_size"] == 25

    def test_get_uses_component_endpoint(self, component, client):
        """get() usa el endpoint del componente."""
        client.get.return_value = paginated_response([])

        component.get()

        assert client.get.call_args[0][0] == component.endpoint

    def test_get_uses_overwrite_endpoint(self, component, client):
        """get() usa overwrite_endpoint cuando se especifica."""
        client.get.return_value = paginated_response([])

        component.get(overwrite_endpoint="/other/endpoint/")

        assert client.get.call_args[0][0] == "/other/endpoint/"

    def test_get_uses_overwrite_schema(self, component, client):
        """get() usa overwrite_schema para parsear los items."""
        client.get.return_value = paginated_response([self.valid_export_item])

        result = component.get(overwrite_schema=self.export_schema)

        assert isinstance(result.results[0], self.export_schema)

    def test_get_passes_extra_kwargs_as_query_params(self, component, client):
        """get() pasa kwargs adicionales como parámetros de consulta."""
        client.get.return_value = paginated_response([])

        component.get(search="test", owner=True)

        call_params = client.get.call_args[1]["query"]
        assert call_params["search"] == "test"
        assert call_params["owner"] is True

    def test_get_validate_false_returns_model(self, component, client):
        """get() con validate=False construye modelos sin validación."""
        client.get.return_value = paginated_response([self.valid_item])

        result = component.get(validate=False)

        assert isinstance(result.results[0], self.schema)

    # ── get_all ───────────────────────────────────────────────────────────────

    def test_get_all_returns_paginated_result(self, component, client):
        """get_all() devuelve PaginatedResult con todos los items."""
        client.get_all.return_value = paginated_response([self.valid_item])

        result = component.get_all()

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], self.schema)

    def test_get_all_sends_page_size(self, component, client):
        """get_all() envía el page_size al cliente."""
        client.get_all.return_value = paginated_response([])

        component.get_all(page_size=100)

        call_params = client.get_all.call_args[1]["query"]
        assert call_params["page_size"] == 100

    def test_get_all_uses_overwrite_endpoint(self, component, client):
        """get_all() usa overwrite_endpoint cuando se especifica."""
        client.get_all.return_value = paginated_response([])

        component.get_all(overwrite_endpoint="/other/endpoint/")

        assert client.get_all.call_args[0][0] == "/other/endpoint/"

    def test_get_all_uses_overwrite_schema(self, component, client):
        """get_all() usa overwrite_schema para parsear los items."""
        client.get_all.return_value = paginated_response([self.valid_export_item])

        result = component.get_all(overwrite_schema=self.export_schema)

        assert isinstance(result.results[0], self.export_schema)

    # ── where ─────────────────────────────────────────────────────────────────

    def test_where_returns_api_query(self, component):
        """where() devuelve un APIQuery sin ejecutar peticiones."""
        assert isinstance(component.where(), APIQuery)

    def test_where_uses_component_endpoint(self, component):
        """where() configura el endpoint del componente en el APIQuery."""
        assert component.where().endpoint == component.endpoint

    def test_where_uses_overwrite_endpoint(self, component):
        """where() usa overwrite_endpoint cuando se especifica."""
        assert component.where(overwrite_endpoint="/other/").endpoint == "/other/"

    def test_where_uses_overwrite_schema(self, component):
        """where() usa overwrite_schema en el APIQuery."""
        assert component.where(overwrite_schema=self.export_schema).schema is self.export_schema

    def test_where_passes_filter_fn(self, component):
        """where() pasa filter_fn al APIQuery."""
        fn = lambda item: True
        assert component.where(filter_fn=fn).filter_fn is fn

    def test_where_passes_page_size(self, component):
        """where() pasa page_size al APIQuery."""
        assert component.where(page_size=25)._page_size == 25

    def test_where_passes_query_params(self, component):
        """where() pasa los parámetros de query al APIQuery."""
        query = component.where(search="test", owner=True)
        assert query.query["search"] == "test"
        assert query.query["owner"] is True

    # ── find ──────────────────────────────────────────────────────────────────

    def test_find_returns_model(self, component, client):
        """find() devuelve una instancia del schema."""
        client.get_one.return_value = self.valid_item

        result = component.find(self.find_pk)

        assert isinstance(result, self.schema)

    def test_find_calls_correct_endpoint(self, component, client):
        """find() construye el endpoint con el pk correctamente."""
        client.get_one.return_value = self.valid_item

        component.find(self.find_pk)

        called = client.get_one.call_args[0][0]
        assert str(self.find_pk) in called
        assert component.endpoint.rstrip("/") in called

    def test_find_uses_overwrite_endpoint(self, component, client):
        """find() usa overwrite_endpoint cuando se especifica."""
        client.get_one.return_value = self.valid_item

        component.find(self.find_pk, overwrite_endpoint="/other/endpoint/")

        assert "/other/endpoint/" in client.get_one.call_args[0][0]

    def test_find_uses_overwrite_schema(self, component, client):
        """find() usa overwrite_schema para parsear el resultado."""
        client.get_one.return_value = self.valid_export_item

        result = component.find(self.find_pk, overwrite_schema=self.export_schema)

        assert isinstance(result, self.export_schema)

    def test_find_validate_false_returns_model(self, component, client):
        """find() con validate=False construye el modelo sin validación."""
        client.get_one.return_value = self.valid_item

        result = component.find(self.find_pk, validate=False)

        assert isinstance(result, self.schema)

    def test_find_handles_paginated_response(self, component, client):
        """find() extrae el primer resultado si el servidor devuelve paginación."""
        client.get_one.return_value = paginated_response([self.valid_item])

        result = component.find(self.find_pk)

        assert isinstance(result, self.schema)

    def test_find_raises_if_paginated_response_is_empty(self, component, client):
        """find() lanza KeyError si la respuesta paginada está vacía."""
        client.get_one.return_value = paginated_response([])

        with pytest.raises(KeyError):
            component.find(999999)

    # ── export ────────────────────────────────────────────────────────────────

    def test_export_returns_list_when_file_is_none(self, component, client):
        """export() devuelve lista de modelos cuando file=None."""
        client.get_all.return_value = paginated_response([self.valid_export_item])

        result = component.export(file=None)

        assert isinstance(result, list)
        assert isinstance(result[0], self.export_schema)

    def test_export_uses_export_schema_by_default(self, component, client):
        """export() usa export_schema del componente por defecto."""
        client.get_all.return_value = paginated_response([self.valid_export_item])

        result = component.export(file=None)

        assert isinstance(result[0], self.export_schema)

    def test_export_uses_export_endpoint_by_default(self, component, client):
        """export() usa export_endpoint del componente si está definido."""
        client.get_all.return_value = paginated_response([])

        component.export(file=None)

        expected = component.export_endpoint or component.endpoint
        assert client.get_all.call_args[0][0] == expected

    def test_export_uses_overwrite_endpoint(self, component, client):
        """export() usa overwrite_endpoint cuando se especifica."""
        client.get_all.return_value = paginated_response([])

        component.export(file=None, overwrite_endpoint="/other/export/")

        assert client.get_all.call_args[0][0] == "/other/export/"

    def test_export_uses_overwrite_schema(self, component, client):
        """export() usa overwrite_schema cuando se especifica."""
        client.get_all.return_value = paginated_response([self.valid_item])

        result = component.export(file=None, overwrite_schema=self.schema)

        assert isinstance(result[0], self.schema)

    def test_export_writes_csv_when_file_provided(self, component, client, tmp_path):
        """export() escribe CSV y devuelve Path cuando se indica file."""
        client.get_all.return_value = paginated_response([self.valid_export_item])
        out = tmp_path / "export.csv"
        client._select_file.return_value = out
        client._write_csv = MagicMock()

        result = component.export(file=out)

        assert isinstance(result, Path)
        client._write_csv.assert_called_once()

    def test_export_validate_false_constructs_without_validation(self, component, client):
        """export() con validate=False construye modelos sin validación."""
        client.get_all.return_value = paginated_response([self.valid_export_item])

        result = component.export(file=None, validate=False)

        assert isinstance(result[0], self.export_schema)


# ── clase base e2e tests ──────────────────────────────────────────────────────

class ComponentE2ETestBase:
    """
    Base class for TrapperComponent e2e tests.

    Subclasses must define:
        component_class: The TrapperComponent subclass to test.
        schema: The main Pydantic schema class.
        export_schema: The export Pydantic schema class.
        env_pk_var: Environment variable name holding a valid pk (for find tests).
    """

    component_class: type
    schema: type[BaseModel]
    export_schema: type[BaseModel]
    env_pk_var: str = ""

    @pytest.fixture(scope="class")
    def component(self, real_api_base):
        return self.component_class(real_api_base)

    def _get_pk(self) -> str:
        return os.getenv(self.env_pk_var, "").strip() if self.env_pk_var else ""

    # ── get ───────────────────────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_get_returns_paginated_result(self, component):
        """get() devuelve PaginatedResult con la primera página."""
        result = component.get(page_size=5)

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results, list)
        assert result.pagination.page == 1

    @pytest.mark.e2e
    def test_get_returns_schema_instances(self, component):
        """get() devuelve instancias del schema configurado."""
        result = component.get(page_size=5)

        if not result.results:
            pytest.skip("No results available on this server")

        for item in result.results:
            assert isinstance(item, self.schema)

    @pytest.mark.e2e
    def test_get_page_size_is_respected(self, component):
        """El número de resultados no supera el page_size solicitado."""
        result = component.get(page_size=3)

        assert len(result.results) <= 3

    @pytest.mark.e2e
    def test_get_validate_false_returns_models(self, component):
        """get() con validate=False devuelve modelos construidos sin validación."""
        result = component.get(page_size=5, validate=False)

        if not result.results:
            pytest.skip("No results available on this server")

        assert all(isinstance(item, self.schema) for item in result.results)

    @pytest.mark.e2e
    def test_get_with_overwrite_schema(self, component):
        """get() con overwrite_schema devuelve instancias del schema indicado."""
        result = component.get(page_size=5, overwrite_schema=self.export_schema)

        if not result.results:
            pytest.skip("No results available on this server")

        assert all(isinstance(item, self.export_schema) for item in result.results)

    # ── get_all ───────────────────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_get_all_count_matches_pagination(self, component):
        """get_all() devuelve tantos items como indica pagination.count."""
        result = component.get_all(page_size=50)

        assert len(result.results) == result.pagination.count

    @pytest.mark.e2e
    def test_get_all_returns_schema_instances(self, component):
        """get_all() devuelve instancias del schema configurado."""
        result = component.get_all(page_size=50)

        for item in result.results:
            assert isinstance(item, self.schema)

    @pytest.mark.e2e
    def test_get_all_no_duplicate_pks(self, component):
        """get_all() no devuelve items duplicados entre páginas."""
        result = component.get_all(page_size=10)

        if not result.results:
            pytest.skip("No results available on this server")

        pks = [item.pk for item in result.results]
        assert len(pks) == len(set(pks))

    # ── where ─────────────────────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_where_returns_api_query(self, component):
        """where() devuelve un APIQuery."""
        assert isinstance(component.where(page_size=5), APIQuery)

    @pytest.mark.e2e
    def test_where_iterates_and_returns_schema_instances(self, component):
        """Iterar where() devuelve instancias del schema."""
        items = []
        for item in component.where(page_size=10):
            items.append(item)
            if len(items) >= 5:
                break

        if not items:
            pytest.skip("No results available on this server")

        assert all(isinstance(item, self.schema) for item in items)

    @pytest.mark.e2e
    def test_where_context_manager_exhausts_on_exit(self, component):
        """where() como context manager queda exhausto al salir."""
        with component.where(page_size=5) as query:
            first = next(query, None)

        assert query._exhausted is True

    @pytest.mark.e2e
    def test_where_filter_fn_filters_results(self, component):
        """where() con filter_fn filtra correctamente los resultados."""
        all_items = list(component.where(page_size=50))

        if not all_items:
            pytest.skip("No results available on this server")

        target_pk = all_items[0].pk
        filtered = list(component.where(
            page_size=50,
            filter_fn=lambda item: item.pk == target_pk,
        ))

        assert len(filtered) == 1
        assert filtered[0].pk == target_pk

    # ── find ──────────────────────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_find_returns_schema_instance(self, component):
        """find(pk) devuelve la instancia del schema correcta."""
        pk = self._get_pk()
        if not pk:
            pytest.skip(f"Set {self.env_pk_var} to run this test")

        result = component.find(int(pk))

        assert isinstance(result, self.schema)
        assert result.pk == int(pk)

    @pytest.mark.e2e
    def test_find_validate_false_returns_model(self, component):
        """find() con validate=False devuelve modelo construido sin validación."""
        pk = self._get_pk()
        if not pk:
            pytest.skip(f"Set {self.env_pk_var} to run this test")

        result = component.find(int(pk), validate=False)

        assert isinstance(result, self.schema)

    @pytest.mark.e2e
    def test_find_nonexistent_pk_raises(self, component):
        """find() lanza excepción para un pk que no existe."""
        with pytest.raises(Exception):
            component.find(999999999)

    # ── export ────────────────────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_export_file_none_returns_list(self, component):
        """export() sin file devuelve lista de instancias del export_schema."""
        result = component.export(file=None)

        assert isinstance(result, list)
        if result:
            assert isinstance(result[0], self.export_schema)

    @pytest.mark.e2e
    def test_export_to_csv_writes_file(self, component, tmp_path):
        """export() escribe CSV y devuelve Path."""
        out = tmp_path / "export.csv"
        result = component.export(file=out)

        assert isinstance(result, Path)
        assert out.exists()
        assert out.stat().st_size > 0

    @pytest.mark.e2e
    def test_export_csv_row_count_matches_get_all(self, component, tmp_path):
        """El CSV exportado tiene tantas filas como indica get_all."""
        expected = component.get_all(page_size=50).pagination.count

        if expected == 0:
            pytest.skip("No results available on this server")

        out = tmp_path / "export.csv"
        component.export(file=out)

        lines = out.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) - 1 == expected  # descontar cabecera