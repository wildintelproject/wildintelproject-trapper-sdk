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
from trapper_client.schemas import (
    ClassificationProject,
    ClassificationProjectCollection,
    ClassificationResourceRecord,
    PaginatedResult,
)


# ── datos de prueba ───────────────────────────────────────────────────────────

VALID_PROJECT ={
      "pk": 60,
      "name": "3rd test",
      "owner": "Jorge García",
      "owner_profile": "/accounts/profile/jorga.garcia@dci.uhu.es/",
      "classificator": 32,
      "research_project": "LERP_01",
      "status": "Ongoing",
      "is_active": True,
      "project_roles": [
        {
          "user": "Jorge García",
          "username": "jorge.garcia@dci.uhu.es",
          "profile": "/accounts/profile/jorge.garcia@dci.uhu.es/",
          "is_superuser": False,
          "roles": [
            "Admin"
          ]
        }
      ],
      "classificator_removed":False,
      "update_data": "/media_classification/project/update/60/",
      "detail_data": "/media_classification/project/detail/60/",
      "delete_data": "/media_classification/project/delete/60/"
    }
VALID_COLLECTION = {
      "pk": 35,
      "collection_pk": 47,
      "name": "R0033",
      "status": "Private",
      "is_active": True,
      "detail_data": "/storage/collection/detail/47/",
      "classify_data": "/media_classification/classify/33/35/",
      "approved_count": 29,
      "classified_count": 1,
      "total_count": 824
    }

VALID_RESOURCE = {
    "pk": 4831,
    "name": "IMG_0001.JPG",
    "thumbnail_url": "/storage/media/4831/thumbnail/",
    "url": "/storage/media/4831/pfile/",
    "mime": "image/jpeg",
    "resource_type": "I",
    "date_recorded": "2024-01-01T08:00:00Z",
    "sequence": "seq-1",
    "classification_data": {
        "pk": 100,
        "url": "/media_classification/classify/33/100/",
        "is_approved": True,
        "is_classified": True,
    },
}

PROJECT_PK = 60
COLLECTION_PK = 47
LINK_PK = 35


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
        mock_links = [
            MagicMock(pk=10, collection_pk=42),
            MagicMock(pk=11, collection_pk=43),
            MagicMock(pk=12, collection_pk=44),
        ]
        component.where_project_collections = MagicMock(return_value=iter(mock_links))

        result = component.find_collection_in_project(
            project_pk=PROJECT_PK, collection_pk=42
        )

        assert result == 10


# ── tests específicos de resources dentro de una collection ─────────────────

class TestClassificationProjectCollectionResources:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return ClassificationProjectsComponent(client)

    def _expected_endpoint(self, component):
        return component._resources_entrypoint(LINK_PK)

    # ── _resources_entrypoint ─────────────────────────────────────────────────

    def test_resources_entrypoint_builds_correct_url(self, component):
        """_resources_entrypoint() construye el endpoint correcto."""
        result = component._resources_entrypoint(LINK_PK)
        assert result == f"media_classification/api/collection/{LINK_PK}/resources/"

    # ── get_collection_resources ──────────────────────────────────────────────

    def test_get_collection_resources_returns_paginated_result(self, component, client):
        """get_collection_resources() devuelve PaginatedResult con items tipados."""
        client.get.return_value = paginated_response([VALID_RESOURCE])

        result = component.get_collection_resources(collection_pk=LINK_PK)

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], ClassificationResourceRecord)

    def test_get_collection_resources_uses_correct_endpoint(self, component, client):
        """get_collection_resources() usa el endpoint de resources de la collection."""
        client.get.return_value = paginated_response([])

        component.get_collection_resources(collection_pk=LINK_PK)

        assert client.get.call_args[0][0] == self._expected_endpoint(component)

    def test_get_collection_resources_passes_extra_kwargs(self, component, client):
        """get_collection_resources() pasa kwargs como parámetros de consulta."""
        client.get.return_value = paginated_response([])

        component.get_collection_resources(collection_pk=LINK_PK, species=42)

        params = client.get.call_args[1]["query"]
        assert params["species"] == 42

    # ── where_collection_resources ────────────────────────────────────────────

    def test_where_collection_resources_returns_api_query(self, component):
        """where_collection_resources() devuelve un APIQuery."""
        assert isinstance(component.where_collection_resources(collection_pk=LINK_PK), APIQuery)

    def test_where_collection_resources_uses_correct_endpoint(self, component):
        """where_collection_resources() configura el endpoint correcto."""
        query = component.where_collection_resources(collection_pk=LINK_PK)
        assert query.endpoint == self._expected_endpoint(component)

    def test_where_collection_resources_uses_correct_schema(self, component):
        """where_collection_resources() usa ClassificationResourceRecord como schema."""
        query = component.where_collection_resources(collection_pk=LINK_PK)
        assert query.schema is ClassificationResourceRecord

    # ── get_all_collection_resources ──────────────────────────────────────────

    def test_get_all_collection_resources_returns_paginated_result(self, component, client):
        """get_all_collection_resources() devuelve PaginatedResult con todos los items."""
        client.get_all.return_value = paginated_response([VALID_RESOURCE])

        result = component.get_all_collection_resources(collection_pk=LINK_PK)

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], ClassificationResourceRecord)

    def test_get_all_collection_resources_uses_correct_endpoint(self, component, client):
        """get_all_collection_resources() usa el endpoint de resources de la collection."""
        client.get_all.return_value = paginated_response([])

        component.get_all_collection_resources(collection_pk=LINK_PK)

        assert client.get_all.call_args[0][0] == self._expected_endpoint(component)

    # ── get_collection_resources_around ───────────────────────────────────────

    def test_get_collection_resources_around_uses_current_and_size_params(self, component, client):
        """get_collection_resources_around() envía current y size como query params."""
        client.get.return_value = paginated_response([VALID_RESOURCE])

        component.get_collection_resources_around(collection_pk=LINK_PK, resource_pk=4831, size=3)

        assert client.get.call_args[0][0] == self._expected_endpoint(component)
        params = client.get.call_args[1]["query"]
        assert params["current"] == 4831
        assert params["size"] == 3

    def test_get_collection_resources_around_default_size(self, component, client):
        """get_collection_resources_around() usa size=5 por defecto."""
        client.get.return_value = paginated_response([])

        component.get_collection_resources_around(collection_pk=LINK_PK, resource_pk=4831)

        params = client.get.call_args[1]["query"]
        assert params["size"] == 5

    def test_get_collection_resources_around_returns_typed_items(self, component, client):
        """get_collection_resources_around() devuelve items tipados como ClassificationResourceRecord."""
        client.get.return_value = paginated_response([VALID_RESOURCE])

        result = component.get_collection_resources_around(collection_pk=LINK_PK, resource_pk=4831)

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], ClassificationResourceRecord)

    def test_get_collection_resources_around_exposes_total_and_filtered(self, component, client):
        """get_collection_resources_around() propaga pagination.total/filtered del servidor."""
        client.get.return_value = {
            "pagination": {"total": 824, "filtered": 120},
            "results": [VALID_RESOURCE],
        }

        result = component.get_collection_resources_around(collection_pk=LINK_PK, resource_pk=4831)

        assert result.pagination.total == 824
        assert result.pagination.filtered == 120

    def test_get_collection_resources_around_passes_extra_kwargs(self, component, client):
        """get_collection_resources_around() pasa kwargs como parámetros de consulta adicionales."""
        client.get.return_value = paginated_response([])

        component.get_collection_resources_around(collection_pk=LINK_PK, resource_pk=4831, species=42)

        params = client.get.call_args[1]["query"]
        assert params["species"] == 42