"""
Unit tests for ClassificationProjectsComponent.

Covers inherited TrapperComponent behaviour plus the project-collections
specific methods.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import ComponentUnitTestBase, paginated_response
from trapper_client.api_query import APIQuery
from trapper_client.components.classification_projects import ClassificationProjectsComponent
from trapper_client.schemas import ClassificationProject, ClassificationProjectCollection, PaginatedResult


# ── datos de prueba ───────────────────────────────────────────────────────────

VALID_PROJECT = {"pk": 1, "name": "Classification Project A"}
VALID_COLLECTION = {"pk": 10, "collection_pk": 42, "name": "Collection A"}

PROJECT_PK = 7
COLLECTION_PK = 42
LINK_PK = 10


# ── tests heredados ───────────────────────────────────────────────────────────

class TestClassificationProjectsComponent(ComponentUnitTestBase):
    component_class = ClassificationProjectsComponent
    schema = ClassificationProject
    export_schema = ClassificationProject
    find_pk = 1
    valid_item = VALID_PROJECT
    valid_export_item = VALID_PROJECT


# ── tests específicos de colecciones ─────────────────────────────────────────

class TestClassificationProjectCollections:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return ClassificationProjectsComponent(client)

    def _expected_endpoint(self, component):
        return component._collections_entrypoint(PROJECT_PK)

    # ── _collections_entrypoint ───────────────────────────────────────────────

    def test_collections_entrypoint_builds_correct_url(self, component):
        """_collections_entrypoint() construye el endpoint correcto."""
        result = component._collections_entrypoint(PROJECT_PK)
        assert result == f"/media_classification/api/project/{PROJECT_PK}/collections"

    # ── get_project_collections ───────────────────────────────────────────────

    def test_get_project_collections_returns_paginated_result(self, component, client):
        """get_project_collections() devuelve PaginatedResult con items tipados."""
        client.get.return_value = paginated_response([VALID_COLLECTION])

        result = component.get_project_collections(project_pk=PROJECT_PK)

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], ClassificationProjectCollection)

    def test_get_project_collections_uses_correct_endpoint(self, component, client):
        """get_project_collections() usa el endpoint de colecciones del proyecto."""
        client.get.return_value = paginated_response([])

        component.get_project_collections(project_pk=PROJECT_PK)

        assert client.get.call_args[0][0] == self._expected_endpoint(component)

    def test_get_project_collections_sends_page_and_page_size(self, component, client):
        """get_project_collections() envía page y page_size al cliente."""
        client.get.return_value = paginated_response([])

        component.get_project_collections(project_pk=PROJECT_PK, page=2, page_size=25)

        params = client.get.call_args[1]["query"]
        assert params["page"] == 2
        assert params["page_size"] == 25

    def test_get_project_collections_passes_extra_kwargs(self, component, client):
        """get_project_collections() pasa kwargs como parámetros de consulta."""
        client.get.return_value = paginated_response([])

        component.get_project_collections(project_pk=PROJECT_PK, search="test")

        params = client.get.call_args[1]["query"]
        assert params["search"] == "test"

    def test_get_project_collections_validate_false_returns_models(self, component, client):
        """get_project_collections() con validate=False construye sin validación."""
        client.get.return_value = paginated_response([VALID_COLLECTION])

        result = component.get_project_collections(project_pk=PROJECT_PK, validate=False)

        assert isinstance(result.results[0], ClassificationProjectCollection)

    # ── get_all_project_collections ───────────────────────────────────────────

    def test_get_all_project_collections_returns_paginated_result(self, component, client):
        """get_all_project_collections() devuelve PaginatedResult con todos los items."""
        client.get_all.return_value = paginated_response([VALID_COLLECTION])

        result = component.get_all_project_collections(project_pk=PROJECT_PK)

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], ClassificationProjectCollection)

    def test_get_all_project_collections_uses_correct_endpoint(self, component, client):
        """get_all_project_collections() usa el endpoint de colecciones del proyecto."""
        client.get_all.return_value = paginated_response([])

        component.get_all_project_collections(project_pk=PROJECT_PK)

        assert client.get_all.call_args[0][0] == self._expected_endpoint(component)

    def test_get_all_project_collections_sends_page_size(self, component, client):
        """get_all_project_collections() envía page_size al cliente."""
        client.get_all.return_value = paginated_response([])

        component.get_all_project_collections(project_pk=PROJECT_PK, page_size=100)

        params = client.get_all.call_args[1]["query"]
        assert params["page_size"] == 100

    def test_get_all_project_collections_validate_false_returns_models(self, component, client):
        """get_all_project_collections() con validate=False construye sin validación."""
        client.get_all.return_value = paginated_response([VALID_COLLECTION])

        result = component.get_all_project_collections(project_pk=PROJECT_PK, validate=False)

        assert isinstance(result.results[0], ClassificationProjectCollection)

    # ── where_project_collections ─────────────────────────────────────────────

    def test_where_project_collections_returns_api_query(self, component):
        """where_project_collections() devuelve un APIQuery."""
        assert isinstance(component.where_project_collections(project_pk=PROJECT_PK), APIQuery)

    def test_where_project_collections_uses_correct_endpoint(self, component):
        """where_project_collections() configura el endpoint correcto."""
        query = component.where_project_collections(project_pk=PROJECT_PK)
        assert query.endpoint == self._expected_endpoint(component)

    def test_where_project_collections_uses_correct_schema(self, component):
        """where_project_collections() usa ClassificationProjectCollection como schema."""
        query = component.where_project_collections(project_pk=PROJECT_PK)
        assert query.schema is ClassificationProjectCollection

    def test_where_project_collections_passes_page_size(self, component):
        """where_project_collections() pasa page_size al APIQuery."""
        query = component.where_project_collections(project_pk=PROJECT_PK, page_size=25)
        assert query._page_size == 25

    def test_where_project_collections_passes_extra_kwargs(self, component):
        """where_project_collections() pasa kwargs como parámetros de consulta."""
        query = component.where_project_collections(project_pk=PROJECT_PK, search="test")
        assert query.query["search"] == "test"

    def test_where_project_collections_validate_false(self, component):
        """where_project_collections() pasa validate=False al APIQuery."""
        query = component.where_project_collections(project_pk=PROJECT_PK, validate=False)
        assert query.validate is False

    # ── find_project_collection ───────────────────────────────────────────────

    def test_find_project_collection_returns_model(self, component, client):
        """find_project_collection() devuelve instancia de ClassificationProjectCollection."""
        client.get_one.return_value = VALID_COLLECTION

        result = component.find_project_collection(project_pk=PROJECT_PK, pk=LINK_PK)

        assert isinstance(result, ClassificationProjectCollection)

    def test_find_project_collection_uses_correct_endpoint(self, component, client):
        """find_project_collection() construye el endpoint con project_pk y pk."""
        client.get_one.return_value = VALID_COLLECTION

        component.find_project_collection(project_pk=PROJECT_PK, pk=LINK_PK)

        called = client.get_one.call_args[0][0]
        assert f"/media_classification/api/project/{PROJECT_PK}/collections" in called
        assert str(LINK_PK) in called

    def test_find_project_collection_validate_false_returns_model(self, component, client):
        """find_project_collection() con validate=False construye sin validación."""
        client.get_one.return_value = VALID_COLLECTION

        result = component.find_project_collection(
            project_pk=PROJECT_PK, pk=LINK_PK, validate=False
        )

        assert isinstance(result, ClassificationProjectCollection)

    # ── find_collection_in_project ────────────────────────────────────────────

    def test_find_collection_in_project_returns_link_pk_when_found(self, component, client):
        """find_collection_in_project() devuelve el pk del link cuando la colección existe."""
        client.get.return_value = paginated_response([VALID_COLLECTION])

        result = component.find_collection_in_project(
            project_pk=PROJECT_PK, collection_pk=COLLECTION_PK
        )

        assert result == LINK_PK

    def test_find_collection_in_project_returns_none_when_not_found(self, component, client):
        """find_collection_in_project() devuelve None cuando la colección no está en el proyecto."""
        client.get.return_value = paginated_response([VALID_COLLECTION])

        result = component.find_collection_in_project(
            project_pk=PROJECT_PK, collection_pk=999
        )

        assert result is None

    def test_find_collection_in_project_returns_none_when_empty(self, component, client):
        """find_collection_in_project() devuelve None cuando no hay colecciones."""
        client.get.return_value = paginated_response([])

        result = component.find_collection_in_project(
            project_pk=PROJECT_PK, collection_pk=COLLECTION_PK
        )

        assert result is None

    def test_find_collection_in_project_stops_at_first_match(self, component, client):
        """find_collection_in_project() no consume más páginas tras encontrar el resultado."""
        collections = [
            {"pk": 10, "collection_pk": 42, "name": "A"},
            {"pk": 11, "collection_pk": 43, "name": "B"},
            {"pk": 12, "collection_pk": 44, "name": "C"},
        ]
        client.get.return_value = paginated_response(collections)

        result = component.find_collection_in_project(
            project_pk=PROJECT_PK, collection_pk=42
        )

        assert result == 10
        assert client.get.call_count == 1