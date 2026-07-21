"""
Unit tests for ResearchProjectsComponent.

Covers both inherited TrapperComponent behaviour and the project-collections
specific methods.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import ComponentUnitTestBase, paginated_response
from trapper_client.api_query import APIQuery
from trapper_client.components.research_projects import ResearchProjectsComponent
from trapper_client.schemas import PaginatedResult, ResearchProject, ResearchProjectCollection


# ── datos de prueba ───────────────────────────────────────────────────────────

VALID_PROJECT = {"pk": 1, "name": "Project A", "acronym": "PA"}
VALID_PROJECT_EXPORT = {"pk": 1, "name": "Project A", "acronym": "PA"}

VALID_COLLECTION = {"pk": 10, "name": "Collection A", "project": 1}

PROJECT_PK = 7
COLLECTION_PK = 10


# ── tests heredados ───────────────────────────────────────────────────────────

class TestResearchProjectsComponent(ComponentUnitTestBase):
    component_class = ResearchProjectsComponent
    schema = ResearchProject
    export_schema = ResearchProject     # sin export_schema propio usa schema
    find_pk = 1
    valid_item = VALID_PROJECT
    valid_export_item = VALID_PROJECT_EXPORT


# ── tests específicos de colecciones ─────────────────────────────────────────

@pytest.fixture
def client():
    return MagicMock()


@pytest.fixture
def component(client):
    return ResearchProjectsComponent(client)


class TestResearchProjectCollections:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return ResearchProjectsComponent(client)

    # ── get_project_collections ───────────────────────────────────────────────

    def test_get_project_collections_returns_paginated_result(self, component, client):
        """get_project_collections() devuelve PaginatedResult con items tipados."""
        client.get.return_value = paginated_response([VALID_COLLECTION])

        result = component.get_project_collections(project_pk=PROJECT_PK)

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], ResearchProjectCollection)

    def test_get_project_collections_uses_correct_endpoint(self, component, client):
        """get_project_collections() construye el endpoint con el project_pk."""
        client.get.return_value = paginated_response([])

        component.get_project_collections(project_pk=PROJECT_PK)

        called_endpoint = client.get.call_args[0][0]
        assert f"research/api/project/{PROJECT_PK}/collections" in called_endpoint

    def test_get_project_collections_sends_page_and_page_size(self, component, client):
        """get_project_collections() envía page y page_size al cliente."""
        client.get.return_value = paginated_response([])

        component.get_project_collections(project_pk=PROJECT_PK, page=2, page_size=25)

        call_params = client.get.call_args[1]["query"]
        assert call_params["page"] == 2
        assert call_params["page_size"] == 25

    def test_get_project_collections_validate_false_returns_models(self, component, client):
        """get_project_collections() con validate=False construye sin validación."""
        client.get.return_value = paginated_response([VALID_COLLECTION])

        result = component.get_project_collections(project_pk=PROJECT_PK, validate=False)

        assert isinstance(result.results[0], ResearchProjectCollection)

    def test_get_project_collections_passes_extra_kwargs(self, component, client):
        """get_project_collections() pasa kwargs como parámetros de consulta."""
        client.get.return_value = paginated_response([])

        component.get_project_collections(project_pk=PROJECT_PK, search="test")

        call_params = client.get.call_args[1]["query"]
        assert call_params["search"] == "test"

    # ── get_all_project_collections ───────────────────────────────────────────

    def test_get_all_project_collections_returns_paginated_result(self, component, client):
        """get_all_project_collections() devuelve PaginatedResult con todos los items."""
        client.get_all.return_value = paginated_response([VALID_COLLECTION])

        result = component.get_all_project_collections(project_pk=PROJECT_PK)

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], ResearchProjectCollection)

    def test_get_all_project_collections_uses_correct_endpoint(self, component, client):
        """get_all_project_collections() construye el endpoint con el project_pk."""
        client.get_all.return_value = paginated_response([])

        component.get_all_project_collections(project_pk=PROJECT_PK)

        called_endpoint = client.get_all.call_args[0][0]
        assert f"research/api/project/{PROJECT_PK}/collections" in called_endpoint

    def test_get_all_project_collections_sends_page_size(self, component, client):
        """get_all_project_collections() envía page_size al cliente."""
        client.get_all.return_value = paginated_response([])

        component.get_all_project_collections(project_pk=PROJECT_PK, page_size=100)

        call_params = client.get_all.call_args[1]["query"]
        assert call_params["page_size"] == 100

    def test_get_all_project_collections_validate_false_returns_models(self, component, client):
        """get_all_project_collections() con validate=False construye sin validación."""
        client.get_all.return_value = paginated_response([VALID_COLLECTION])

        result = component.get_all_project_collections(project_pk=PROJECT_PK, validate=False)

        assert isinstance(result.results[0], ResearchProjectCollection)

    # ── where_project_collections ─────────────────────────────────────────────

    def test_where_project_collections_returns_api_query(self, component):
        """where_project_collections() devuelve un APIQuery."""
        result = component.where_project_collections(project_pk=PROJECT_PK)
        assert isinstance(result, APIQuery)

    def test_where_project_collections_uses_correct_endpoint(self, component):
        """where_project_collections() configura el endpoint correcto."""
        query = component.where_project_collections(project_pk=PROJECT_PK)
        assert f"research/api/project/{PROJECT_PK}/collections" in query.endpoint

    def test_where_project_collections_uses_correct_schema(self, component):
        """where_project_collections() usa ResearchProjectCollection como schema."""
        query = component.where_project_collections(project_pk=PROJECT_PK)
        assert query.schema is ResearchProjectCollection

    def test_where_project_collections_passes_page_size(self, component):
        """where_project_collections() pasa page_size al APIQuery."""
        query = component.where_project_collections(project_pk=PROJECT_PK, page_size=25)
        assert query._page_size == 25

    def test_where_project_collections_passes_extra_kwargs(self, component):
        """where_project_collections() pasa kwargs como parámetros de consulta."""
        query = component.where_project_collections(project_pk=PROJECT_PK, search="test")
        assert query.query["search"] == "test"

    # ── find_project_collection ───────────────────────────────────────────────

    def test_find_project_collection_returns_model(self, component, client):
        """find_project_collection() devuelve instancia de ResearchProjectCollection."""
        client.get_one.return_value = VALID_COLLECTION

        result = component.find_project_collection(project_pk=PROJECT_PK, pk=COLLECTION_PK)

        assert isinstance(result, ResearchProjectCollection)

    def test_find_project_collection_uses_correct_endpoint(self, component, client):
        """find_project_collection() construye el endpoint con project_pk y pk."""
        client.get_one.return_value = VALID_COLLECTION

        component.find_project_collection(project_pk=PROJECT_PK, pk=COLLECTION_PK)

        called_endpoint = client.get_one.call_args[0][0]
        assert f"research/api/project/{PROJECT_PK}/collections/{COLLECTION_PK}" in called_endpoint

    def test_find_project_collection_validate_false_returns_model(self, component, client):
        """find_project_collection() con validate=False construye sin validación."""
        client.get_one.return_value = VALID_COLLECTION

        result = component.find_project_collection(
            project_pk=PROJECT_PK, pk=COLLECTION_PK, validate=False
        )

        assert isinstance(result, ResearchProjectCollection)