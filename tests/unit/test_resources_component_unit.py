"""
Unit tests for ResourcesComponent.

Covers both inherited TrapperComponent behaviour and the collection/location
specific sub-endpoint methods.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import ComponentUnitTestBase, paginated_response
from trapper_client.api_query import APIQuery
from trapper_client.components.resources import ResourcesComponent
from trapper_client.schemas import PaginatedResult, Resource


# ── datos de prueba ───────────────────────────────────────────────────────────

VALID_RESOURCE = {"pk": 1, "name": "resource_001.jpg"}
COLLECTION_PK = 5
LOCATION_PK = 42
RESOURCE_PK = 1


# ── tests heredados ───────────────────────────────────────────────────────────

class TestResourcesComponent(ComponentUnitTestBase):
    component_class = ResourcesComponent
    schema = Resource
    export_schema = Resource
    find_pk = RESOURCE_PK
    valid_item = VALID_RESOURCE
    valid_export_item = VALID_RESOURCE


# ── tests sub-endpoints ───────────────────────────────────────────────────────

class TestResourcesByCollection:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return ResourcesComponent(client)

    def _expected_endpoint(self, component):
        return f"{component.endpoint.rstrip('/')}/collection/{COLLECTION_PK}"

    # ── where_by_collection ───────────────────────────────────────────────────

    def test_where_by_collection_returns_api_query(self, component):
        """where_by_collection() devuelve un APIQuery."""
        assert isinstance(component.where_by_collection(COLLECTION_PK), APIQuery)

    def test_where_by_collection_uses_correct_endpoint(self, component):
        """where_by_collection() configura el endpoint de colección."""
        query = component.where_by_collection(COLLECTION_PK)
        assert query.endpoint == self._expected_endpoint(component)

    def test_where_by_collection_passes_page_size(self, component):
        """where_by_collection() pasa page_size al APIQuery."""
        query = component.where_by_collection(COLLECTION_PK, page_size=25)
        assert query._page_size == 25

    def test_where_by_collection_passes_filter_fn(self, component):
        """where_by_collection() pasa filter_fn al APIQuery."""
        fn = lambda item: True
        query = component.where_by_collection(COLLECTION_PK, filter_fn=fn)
        assert query.filter_fn is fn

    def test_where_by_collection_passes_extra_kwargs(self, component):
        """where_by_collection() pasa kwargs como parámetros de consulta."""
        query = component.where_by_collection(COLLECTION_PK, status="Public")
        assert query.query["status"] == "Public"

    def test_where_by_collection_validate_false(self, component):
        """where_by_collection() pasa validate=False al APIQuery."""
        query = component.where_by_collection(COLLECTION_PK, validate=False)
        assert query.validate is False

    # ── get_by_collection ─────────────────────────────────────────────────────

    def test_get_by_collection_returns_paginated_result(self, component, client):
        """get_by_collection() devuelve PaginatedResult con items tipados."""
        client.get.return_value = paginated_response([VALID_RESOURCE])

        result = component.get_by_collection(COLLECTION_PK)

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], Resource)

    def test_get_by_collection_uses_correct_endpoint(self, component, client):
        """get_by_collection() usa el endpoint de colección."""
        client.get.return_value = paginated_response([])

        component.get_by_collection(COLLECTION_PK)

        assert client.get.call_args[0][0] == self._expected_endpoint(component)

    def test_get_by_collection_sends_page_and_page_size(self, component, client):
        """get_by_collection() envía page y page_size al cliente."""
        client.get.return_value = paginated_response([])

        component.get_by_collection(COLLECTION_PK, page=2, page_size=25)

        params = client.get.call_args[1]["query"]
        assert params["page"] == 2
        assert params["page_size"] == 25

    def test_get_by_collection_passes_extra_kwargs(self, component, client):
        """get_by_collection() pasa kwargs como parámetros de consulta."""
        client.get.return_value = paginated_response([])

        component.get_by_collection(COLLECTION_PK, status="Public")

        params = client.get.call_args[1]["query"]
        assert params["status"] == "Public"

    def test_get_by_collection_validate_false_returns_model(self, component, client):
        """get_by_collection() con validate=False construye modelos sin validación."""
        client.get.return_value = paginated_response([VALID_RESOURCE])

        result = component.get_by_collection(COLLECTION_PK, validate=False)

        assert isinstance(result.results[0], Resource)

    # ── get_all_by_collection ─────────────────────────────────────────────────

    def test_get_all_by_collection_returns_paginated_result(self, component, client):
        """get_all_by_collection() devuelve PaginatedResult con todos los items."""
        client.get_all.return_value = paginated_response([VALID_RESOURCE])

        result = component.get_all_by_collection(COLLECTION_PK)

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], Resource)

    def test_get_all_by_collection_uses_correct_endpoint(self, component, client):
        """get_all_by_collection() usa el endpoint de colección."""
        client.get_all.return_value = paginated_response([])

        component.get_all_by_collection(COLLECTION_PK)

        assert client.get_all.call_args[0][0] == self._expected_endpoint(component)

    def test_get_all_by_collection_sends_page_size(self, component, client):
        """get_all_by_collection() envía page_size al cliente."""
        client.get_all.return_value = paginated_response([])

        component.get_all_by_collection(COLLECTION_PK, page_size=100)

        params = client.get_all.call_args[1]["query"]
        assert params["page_size"] == 100

    # ── find_by_collection ────────────────────────────────────────────────────

    def test_find_by_collection_returns_resource(self, component, client):
        """find_by_collection() devuelve instancia de Resource."""
        client.get_one.return_value = VALID_RESOURCE

        result = component.find_by_collection(COLLECTION_PK, RESOURCE_PK)

        assert isinstance(result, Resource)

    def test_find_by_collection_uses_correct_endpoint(self, component, client):
        """find_by_collection() construye el endpoint con collection_pk y resource_pk."""
        client.get_one.return_value = VALID_RESOURCE

        component.find_by_collection(COLLECTION_PK, RESOURCE_PK)

        called = client.get_one.call_args[0][0]
        assert f"collection/{COLLECTION_PK}" in called
        assert str(RESOURCE_PK) in called

    def test_find_by_collection_validate_false_returns_model(self, component, client):
        """find_by_collection() con validate=False construye sin validación."""
        client.get_one.return_value = VALID_RESOURCE

        result = component.find_by_collection(COLLECTION_PK, RESOURCE_PK, validate=False)

        assert isinstance(result, Resource)


class TestResourcesByLocation:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return ResourcesComponent(client)

    def _expected_endpoint(self, component):
        return f"{component.endpoint.rstrip('/')}/location/{LOCATION_PK}"

    # ── where_by_location ─────────────────────────────────────────────────────

    def test_where_by_location_returns_api_query(self, component):
        """where_by_location() devuelve un APIQuery."""
        assert isinstance(component.where_by_location(LOCATION_PK), APIQuery)

    def test_where_by_location_uses_correct_endpoint(self, component):
        """where_by_location() configura el endpoint de localización."""
        query = component.where_by_location(LOCATION_PK)
        assert query.endpoint == self._expected_endpoint(component)

    def test_where_by_location_passes_page_size(self, component):
        """where_by_location() pasa page_size al APIQuery."""
        query = component.where_by_location(LOCATION_PK, page_size=25)
        assert query._page_size == 25

    def test_where_by_location_passes_filter_fn(self, component):
        """where_by_location() pasa filter_fn al APIQuery."""
        fn = lambda item: True
        query = component.where_by_location(LOCATION_PK, filter_fn=fn)
        assert query.filter_fn is fn

    def test_where_by_location_passes_extra_kwargs(self, component):
        """where_by_location() pasa kwargs como parámetros de consulta."""
        query = component.where_by_location(LOCATION_PK, status="Public")
        assert query.query["status"] == "Public"

    def test_where_by_location_validate_false(self, component):
        """where_by_location() pasa validate=False al APIQuery."""
        query = component.where_by_location(LOCATION_PK, validate=False)
        assert query.validate is False

    # ── get_by_location ───────────────────────────────────────────────────────

    def test_get_by_location_returns_paginated_result(self, component, client):
        """get_by_location() devuelve PaginatedResult con items tipados."""
        client.get.return_value = paginated_response([VALID_RESOURCE])

        result = component.get_by_location(LOCATION_PK)

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], Resource)

    def test_get_by_location_uses_correct_endpoint(self, component, client):
        """get_by_location() usa el endpoint de localización."""
        client.get.return_value = paginated_response([])

        component.get_by_location(LOCATION_PK)

        assert client.get.call_args[0][0] == self._expected_endpoint(component)

    def test_get_by_location_sends_page_and_page_size(self, component, client):
        """get_by_location() envía page y page_size al cliente."""
        client.get.return_value = paginated_response([])

        component.get_by_location(LOCATION_PK, page=2, page_size=25)

        params = client.get.call_args[1]["query"]
        assert params["page"] == 2
        assert params["page_size"] == 25

    def test_get_by_location_passes_extra_kwargs(self, component, client):
        """get_by_location() pasa kwargs como parámetros de consulta."""
        client.get.return_value = paginated_response([])

        component.get_by_location(LOCATION_PK, status="Public")

        params = client.get.call_args[1]["query"]
        assert params["status"] == "Public"

    def test_get_by_location_validate_false_returns_model(self, component, client):
        """get_by_location() con validate=False construye modelos sin validación."""
        client.get.return_value = paginated_response([VALID_RESOURCE])

        result = component.get_by_location(LOCATION_PK, validate=False)

        assert isinstance(result.results[0], Resource)

    # ── get_all_by_location ───────────────────────────────────────────────────

    def test_get_all_by_location_returns_paginated_result(self, component, client):
        """get_all_by_location() devuelve PaginatedResult con todos los items."""
        client.get_all.return_value = paginated_response([VALID_RESOURCE])

        result = component.get_all_by_location(LOCATION_PK)

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], Resource)

    def test_get_all_by_location_uses_correct_endpoint(self, component, client):
        """get_all_by_location() usa el endpoint de localización."""
        client.get_all.return_value = paginated_response([])

        component.get_all_by_location(LOCATION_PK)

        assert client.get_all.call_args[0][0] == self._expected_endpoint(component)

    def test_get_all_by_location_sends_page_size(self, component, client):
        """get_all_by_location() envía page_size al cliente."""
        client.get_all.return_value = paginated_response([])

        component.get_all_by_location(LOCATION_PK, page_size=100)

        params = client.get_all.call_args[1]["query"]
        assert params["page_size"] == 100

    # ── find_by_location ──────────────────────────────────────────────────────

    def test_find_by_location_returns_resource(self, component, client):
        """find_by_location() devuelve instancia de Resource."""
        client.get_one.return_value = VALID_RESOURCE

        result = component.find_by_location(LOCATION_PK, RESOURCE_PK)

        assert isinstance(result, Resource)

    def test_find_by_location_uses_correct_endpoint(self, component, client):
        """find_by_location() construye el endpoint con location_pk y resource_pk."""
        client.get_one.return_value = VALID_RESOURCE

        component.find_by_location(LOCATION_PK, RESOURCE_PK)

        called = client.get_one.call_args[0][0]
        assert f"location/{LOCATION_PK}" in called
        assert str(RESOURCE_PK) in called

    def test_find_by_location_validate_false_returns_model(self, component, client):
        """find_by_location() con validate=False construye sin validación."""
        client.get_one.return_value = VALID_RESOURCE

        result = component.find_by_location(LOCATION_PK, RESOURCE_PK, validate=False)

        assert isinstance(result, Resource)