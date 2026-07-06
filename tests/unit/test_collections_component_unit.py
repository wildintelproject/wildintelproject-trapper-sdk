"""
Unit tests for CollectionsComponent.

Covers inherited TrapperComponent behaviour plus the resources,
ondemand, map, and append sub-endpoint methods.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import ComponentUnitTestBase, paginated_response
from trapper_client.api_query import APIQuery
from trapper_client.components.collections import CollectionsComponent
from trapper_client.schemas import Collection, PaginatedResult, Resource


# ── datos de prueba ───────────────────────────────────────────────────────────

VALID_COLLECTION = {"pk": 1, "name": "Collection A"}
VALID_RESOURCE = {"pk": 10, "name": "resource_001.jpg"}
COLLECTION_PK = 3
RESOURCE_PK = 10


# ── endpoints reales (regresión) ──────────────────────────────────────────────
#
# Los tests de cada sub-endpoint (ondemand/map/append) solo comprueban que el
# APIQuery/llamada use `component._X_endpoint`, lo cual es auto-referencial y
# no detecta si esa constante apunta al recurso equivocado. Estos tests fijan
# los valores reales de las rutas del servidor Trapper (`storage/urls.py`).

def test_ondemand_endpoint_matches_server_route():
    """_ondemand_endpoint debe apuntar a collections_ondemand, no a collections_append."""
    assert CollectionsComponent._ondemand_endpoint == "storage/api/collections_ondemand"


def test_append_endpoint_matches_server_route():
    assert CollectionsComponent._append_endpoint == "storage/api/collections_append"


def test_map_endpoint_matches_server_route():
    assert CollectionsComponent._map_endpoint == "storage/api/collections_map"


def test_ondemand_and_append_endpoints_are_distinct():
    """Regresión: _ondemand_endpoint estaba duplicado con _append_endpoint,
    haciendo que where_ondemand/get_ondemand/etc. leyeran el recurso equivocado."""
    assert CollectionsComponent._ondemand_endpoint != CollectionsComponent._append_endpoint


# ── tests heredados ───────────────────────────────────────────────────────────

class TestCollectionsComponent(ComponentUnitTestBase):
    component_class = CollectionsComponent
    schema = Collection
    export_schema = Collection
    find_pk = 1
    valid_item = VALID_COLLECTION
    valid_export_item = VALID_COLLECTION


# ── fixture compartido ────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return MagicMock()


@pytest.fixture
def component(client):
    return CollectionsComponent(client)


# ── resources sub-endpoint ────────────────────────────────────────────────────

class TestCollectionResources:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return CollectionsComponent(client)

# ── ondemand sub-endpoint ─────────────────────────────────────────────────────

class TestCollectionOndemand:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return CollectionsComponent(client)

    # ── where_ondemand ────────────────────────────────────────────────────────

    def test_where_ondemand_returns_api_query(self, component):
        """where_ondemand() devuelve un APIQuery."""
        assert isinstance(component.where_ondemand(), APIQuery)

    def test_where_ondemand_uses_correct_endpoint(self, component):
        """where_ondemand() usa el endpoint ondemand."""
        query = component.where_ondemand()
        assert query.endpoint == component._ondemand_endpoint

    def test_where_ondemand_uses_collection_schema(self, component):
        """where_ondemand() usa Collection como schema."""
        query = component.where_ondemand()
        assert query.schema is Collection

    def test_where_ondemand_passes_extra_kwargs(self, component):
        """where_ondemand() pasa kwargs como parámetros de consulta."""
        query = component.where_ondemand(owner=True)
        assert query.query["owner"] is True

    # ── get_ondemand ──────────────────────────────────────────────────────────

    def test_get_ondemand_returns_paginated_result(self, component, client):
        """get_ondemand() devuelve PaginatedResult con items de tipo Collection."""
        client.get.return_value = paginated_response([VALID_COLLECTION])

        result = component.get_ondemand()

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], Collection)

    def test_get_ondemand_uses_correct_endpoint(self, component, client):
        """get_ondemand() usa el endpoint ondemand."""
        client.get.return_value = paginated_response([])

        component.get_ondemand()

        assert client.get.call_args[0][0] == component._ondemand_endpoint

    def test_get_ondemand_sends_page_and_page_size(self, component, client):
        """get_ondemand() envía page y page_size al cliente."""
        client.get.return_value = paginated_response([])

        component.get_ondemand(page=2, page_size=25)

        params = client.get.call_args[1]["query"]
        assert params["page"] == 2
        assert params["page_size"] == 25

    # ── get_all_ondemand ──────────────────────────────────────────────────────

    def test_get_all_ondemand_returns_paginated_result(self, component, client):
        """get_all_ondemand() devuelve PaginatedResult con todos los items."""
        client.get_all.return_value = paginated_response([VALID_COLLECTION])

        result = component.get_all_ondemand()

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], Collection)

    def test_get_all_ondemand_uses_correct_endpoint(self, component, client):
        """get_all_ondemand() usa el endpoint ondemand."""
        client.get_all.return_value = paginated_response([])

        component.get_all_ondemand()

        assert client.get_all.call_args[0][0] == component._ondemand_endpoint

    # ── find_ondemand ─────────────────────────────────────────────────────────

    def test_find_ondemand_returns_collection(self, component, client):
        """find_ondemand() devuelve instancia de Collection."""
        client.get_one.return_value = VALID_COLLECTION

        result = component.find_ondemand(1)

        assert isinstance(result, Collection)

    def test_find_ondemand_uses_get_one(self, component, client):
        """find_ondemand() usa client.get_one, no client.get."""
        client.get_one.return_value = VALID_COLLECTION

        component.find_ondemand(1)

        client.get_one.assert_called_once()
        client.get.assert_not_called()

    def test_find_ondemand_validate_false_returns_model(self, component, client):
        """find_ondemand() con validate=False construye sin validación."""
        client.get_one.return_value = VALID_COLLECTION

        result = component.find_ondemand(1, validate=False)

        assert isinstance(result, Collection)


# ── map sub-endpoint ──────────────────────────────────────────────────────────

class TestCollectionMap:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return CollectionsComponent(client)

    def test_where_map_returns_api_query(self, component):
        """where_map() devuelve un APIQuery."""
        assert isinstance(component.where_map(), APIQuery)

    def test_where_map_uses_correct_endpoint(self, component):
        """where_map() usa el endpoint map."""
        query = component.where_map()
        assert query.endpoint == component._map_endpoint

    def test_where_map_passes_extra_kwargs(self, component):
        """where_map() pasa kwargs como parámetros de consulta."""
        query = component.where_map(owner=True)
        assert query.query["owner"] is True

    def test_get_map_returns_paginated_result(self, component, client):
        """get_map() devuelve PaginatedResult."""
        client.get.return_value = paginated_response([VALID_COLLECTION])

        result = component.get_map()

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], Collection)

    def test_get_map_uses_correct_endpoint(self, component, client):
        """get_map() usa el endpoint map."""
        client.get.return_value = paginated_response([])

        component.get_map()

        assert client.get.call_args[0][0] == component._map_endpoint

    def test_get_all_map_returns_paginated_result(self, component, client):
        """get_all_map() devuelve PaginatedResult."""
        client.get_all.return_value = paginated_response([VALID_COLLECTION])

        result = component.get_all_map()

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], Collection)

    def test_get_all_map_uses_correct_endpoint(self, component, client):
        """get_all_map() usa el endpoint map."""
        client.get_all.return_value = paginated_response([])

        component.get_all_map()

        assert client.get_all.call_args[0][0] == component._map_endpoint

    def test_find_map_returns_collection(self, component, client):
        """find_map() devuelve instancia de Collection."""
        client.get_one.return_value = VALID_COLLECTION

        result = component.find_map(1)

        assert isinstance(result, Collection)

    def test_find_map_uses_correct_endpoint(self, component, client):
        """find_map() usa el endpoint map."""
        client.get_one.return_value = VALID_COLLECTION

        component.find_map(1)

        called = client.get_one.call_args[0][0]
        assert component._map_endpoint in called

    def test_find_map_validate_false_returns_model(self, component, client):
        """find_map() con validate=False construye sin validación."""
        client.get_one.return_value = VALID_COLLECTION

        result = component.find_map(1, validate=False)

        assert isinstance(result, Collection)


# ── append sub-endpoint ───────────────────────────────────────────────────────

class TestCollectionAppend:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return CollectionsComponent(client)

    def test_where_append_returns_api_query(self, component):
        """where_append() devuelve un APIQuery."""
        assert isinstance(component.where_append(), APIQuery)

    def test_where_append_uses_correct_endpoint(self, component):
        """where_append() usa el endpoint append."""
        query = component.where_append()
        assert query.endpoint == component._append_endpoint

    def test_where_append_passes_extra_kwargs(self, component):
        """where_append() pasa kwargs como parámetros de consulta."""
        query = component.where_append(owner=True)
        assert query.query["owner"] is True

    def test_get_append_returns_paginated_result(self, component, client):
        """get_append() devuelve PaginatedResult."""
        client.get.return_value = paginated_response([VALID_COLLECTION])

        result = component.get_append()

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], Collection)

    def test_get_append_uses_correct_endpoint(self, component, client):
        """get_append() usa el endpoint append."""
        client.get.return_value = paginated_response([])

        component.get_append()

        assert client.get.call_args[0][0] == component._append_endpoint

    def test_get_all_append_returns_paginated_result(self, component, client):
        """get_all_append() devuelve PaginatedResult."""
        client.get_all.return_value = paginated_response([VALID_COLLECTION])

        result = component.get_all_append()

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], Collection)

    def test_get_all_append_uses_correct_endpoint(self, component, client):
        """get_all_append() usa el endpoint append."""
        client.get_all.return_value = paginated_response([])

        component.get_all_append()

        assert client.get_all.call_args[0][0] == component._append_endpoint

    def test_find_append_returns_collection(self, component, client):
        """find_append() devuelve instancia de Collection."""
        client.get_one.return_value = VALID_COLLECTION

        result = component.find_append(1)

        assert isinstance(result, Collection)

    def test_find_append_uses_correct_endpoint(self, component, client):
        """find_append() usa el endpoint append."""
        client.get_one.return_value = VALID_COLLECTION

        component.find_append(1)

        called = client.get_one.call_args[0][0]
        assert component._append_endpoint in called

    def test_find_append_validate_false_returns_model(self, component, client):
        """find_append() con validate=False construye sin validación."""
        client.get_one.return_value = VALID_COLLECTION

        result = component.find_append(1, validate=False)

        assert isinstance(result, Collection)