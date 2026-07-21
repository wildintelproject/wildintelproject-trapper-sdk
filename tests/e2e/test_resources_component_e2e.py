"""
End-to-end tests for ResourcesComponent against a real Trapper server.

Requires environment variables:
    WILDINTEL_BASE_URL, WILDINTEL_ACCESS_TOKEN, WILDINTEL_SMOKE_ENABLED=1

Optional:
    WILDINTEL_RESOURCE_PK     — pk of an existing resource
    WILDINTEL_COLLECTION_PK   — pk of an existing collection
    WILDINTEL_LOCATION_PK     — pk of an existing location
"""
from __future__ import annotations

import os

import pytest

from tests.base_component_tests import ComponentE2ETestBase
from trapper_client.api_query import APIQuery
from trapper_client.components.resources import ResourcesComponent
from trapper_client.schemas import PaginatedResult, Resource


# ── tests heredados ───────────────────────────────────────────────────────────

class TestResourcesComponentE2E(ComponentE2ETestBase):
    component_class = ResourcesComponent
    schema = Resource
    export_schema = Resource
    env_pk_var = "WILDINTEL_RESOURCE_PK"


# ── helpers ───────────────────────────────────────────────────────────────────

def _collection_pk() -> str:
    return os.getenv("WILDINTEL_COLLECTION_PK", "").strip()


def _location_pk() -> str:
    return os.getenv("WILDINTEL_LOCATION_PK", "").strip()


def _resource_pk() -> str:
    return os.getenv("WILDINTEL_RESOURCE_PK", "").strip()


# ── tests sub-endpoint /collection ───────────────────────────────────────────

class TestResourcesByCollectionE2E:

    @pytest.fixture(scope="class")
    def component(self, real_api_base):
        return ResourcesComponent(real_api_base)

    # ── where_by_collection ───────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_where_by_collection_returns_api_query(self, component):
        """where_by_collection() devuelve un APIQuery."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        result = component.where_by_collection(int(pk), page_size=5)
        assert isinstance(result, APIQuery)

    @pytest.mark.e2e
    def test_where_by_collection_iterates_resource_instances(self, component):
        """Iterar where_by_collection() devuelve instancias de Resource."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        items = []
        for res in component.where_by_collection(int(pk), page_size=10):
            items.append(res)
            if len(items) >= 5:
                break

        if not items:
            pytest.skip("No resources available for this collection")

        assert all(isinstance(res, Resource) for res in items)

    @pytest.mark.e2e
    def test_where_by_collection_context_manager_exhausts_on_exit(self, component):
        """where_by_collection() como context manager queda exhausto al salir."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        with component.where_by_collection(int(pk), page_size=5) as query:
            next(query, None)

        assert query._exhausted is True

    @pytest.mark.e2e
    def test_where_by_collection_passes_filter_fn(self, component):
        """where_by_collection() con filter_fn filtra los resultados."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        all_items = list(component.where_by_collection(int(pk), page_size=50))
        if not all_items:
            pytest.skip("No resources available for this collection")

        target_pk = all_items[0].pk
        filtered = list(component.where_by_collection(
            int(pk),
            page_size=50,
            filter_fn=lambda res: res.pk == target_pk,
        ))

        assert len(filtered) == 1
        assert filtered[0].pk == target_pk

    # ── get_by_collection ─────────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_get_by_collection_returns_paginated_result(self, component):
        """get_by_collection() devuelve PaginatedResult."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        result = component.get_by_collection(int(pk), page_size=5)

        assert isinstance(result, PaginatedResult)
        assert result.pagination.page == 1

    @pytest.mark.e2e
    def test_get_by_collection_returns_resource_instances(self, component):
        """get_by_collection() devuelve instancias de Resource."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        result = component.get_by_collection(int(pk), page_size=5)

        if not result.results:
            pytest.skip("No resources available for this collection")

        assert all(isinstance(res, Resource) for res in result.results)

    @pytest.mark.e2e
    def test_get_by_collection_page_size_respected(self, component):
        """get_by_collection() respeta el page_size solicitado."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        result = component.get_by_collection(int(pk), page_size=3)
        assert len(result.results) <= 3

    # ── get_all_by_collection ─────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_get_all_by_collection_count_matches_pagination(self, component):
        """get_all_by_collection() devuelve tantos items como indica pagination.count."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        result = component.get_all_by_collection(int(pk), page_size=50)
        assert len(result.results) == result.pagination.count

    @pytest.mark.e2e
    def test_get_all_by_collection_no_duplicate_pks(self, component):
        """get_all_by_collection() no devuelve items duplicados entre páginas."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        result = component.get_all_by_collection(int(pk), page_size=10)
        if not result.results:
            pytest.skip("No resources available for this collection")

        pks = [res.pk for res in result.results]
        assert len(pks) == len(set(pks))

    # ── find_by_collection ────────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_find_by_collection_returns_resource(self, component):
        """find_by_collection() devuelve la instancia de Resource correcta."""
        collection_pk = _collection_pk()
        resource_pk = _resource_pk()
        if not collection_pk or not resource_pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK and WILDINTEL_RESOURCE_PK to run this test")

        result = component.find_by_collection(int(collection_pk), int(resource_pk))

        assert isinstance(result, Resource)
        assert result.pk == int(resource_pk)

    @pytest.mark.e2e
    def test_find_by_collection_validate_false_returns_model(self, component):
        """find_by_collection() con validate=False devuelve modelo sin validar."""
        collection_pk = _collection_pk()
        resource_pk = _resource_pk()
        if not collection_pk or not resource_pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK and WILDINTEL_RESOURCE_PK to run this test")

        result = component.find_by_collection(
            int(collection_pk), int(resource_pk), validate=False
        )
        assert isinstance(result, Resource)

    @pytest.mark.e2e
    def test_find_by_collection_nonexistent_raises(self, component):
        """find_by_collection() lanza excepción para resource_pk inexistente."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        with pytest.raises(Exception):
            component.find_by_collection(int(pk), 999999999)


# ── tests sub-endpoint /location ──────────────────────────────────────────────

class TestResourcesByLocationE2E:

    @pytest.fixture(scope="class")
    def component(self, real_api_base):
        return ResourcesComponent(real_api_base)

    # ── where_by_location ─────────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_where_by_location_returns_api_query(self, component):
        """where_by_location() devuelve un APIQuery."""
        pk = _location_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

        result = component.where_by_location(int(pk), page_size=5)
        assert isinstance(result, APIQuery)

    @pytest.mark.e2e
    def test_where_by_location_iterates_resource_instances(self, component):
        """Iterar where_by_location() devuelve instancias de Resource."""
        pk = _location_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

        items = []
        for res in component.where_by_location(int(pk), page_size=10):
            items.append(res)
            if len(items) >= 5:
                break

        if not items:
            pytest.skip("No resources available for this location")

        assert all(isinstance(res, Resource) for res in items)

    @pytest.mark.e2e
    def test_where_by_location_context_manager_exhausts_on_exit(self, component):
        """where_by_location() como context manager queda exhausto al salir."""
        pk = _location_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

        with component.where_by_location(int(pk), page_size=5) as query:
            next(query, None)

        assert query._exhausted is True

    # ── get_by_location ───────────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_get_by_location_returns_paginated_result(self, component):
        """get_by_location() devuelve PaginatedResult."""
        pk = _location_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

        result = component.get_by_location(int(pk), page_size=5)

        assert isinstance(result, PaginatedResult)
        assert result.pagination.page == 1

    @pytest.mark.e2e
    def test_get_by_location_returns_resource_instances(self, component):
        """get_by_location() devuelve instancias de Resource."""
        pk = _location_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

        result = component.get_by_location(int(pk), page_size=5)

        if not result.results:
            pytest.skip("No resources available for this location")

        assert all(isinstance(res, Resource) for res in result.results)

    @pytest.mark.e2e
    def test_get_by_location_page_size_respected(self, component):
        """get_by_location() respeta el page_size solicitado."""
        pk = _location_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

        result = component.get_by_location(int(pk), page_size=3)
        assert len(result.results) <= 3

    # ── get_all_by_location ───────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_get_all_by_location_count_matches_pagination(self, component):
        """get_all_by_location() devuelve tantos items como indica pagination.count."""
        pk = _location_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

        result = component.get_all_by_location(int(pk), page_size=50)
        assert len(result.results) == result.pagination.count

    @pytest.mark.e2e
    def test_get_all_by_location_no_duplicate_pks(self, component):
        """get_all_by_location() no devuelve items duplicados entre páginas."""
        pk = _location_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

        result = component.get_all_by_location(int(pk), page_size=10)
        if not result.results:
            pytest.skip("No resources available for this location")

        pks = [res.pk for res in result.results]
        assert len(pks) == len(set(pks))

    # ── find_by_location ──────────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_find_by_location_returns_resource(self, component):
        """find_by_location() devuelve la instancia de Resource correcta."""
        location_pk = _location_pk()
        resource_pk = _resource_pk()
        if not location_pk or not resource_pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK and WILDINTEL_RESOURCE_PK to run this test")

        result = component.find_by_location(int(location_pk), int(resource_pk))

        assert isinstance(result, Resource)
        assert result.pk == int(resource_pk)

    @pytest.mark.e2e
    def test_find_by_location_validate_false_returns_model(self, component):
        """find_by_location() con validate=False devuelve modelo sin validar."""
        location_pk = _location_pk()
        resource_pk = _resource_pk()
        if not location_pk or not resource_pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK and WILDINTEL_RESOURCE_PK to run this test")

        result = component.find_by_location(
            int(location_pk), int(resource_pk), validate=False
        )
        assert isinstance(result, Resource)

    @pytest.mark.e2e
    def test_find_by_location_nonexistent_raises(self, component):
        """find_by_location() lanza excepción para resource_pk inexistente."""
        pk = _location_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

        with pytest.raises(Exception):
            component.find_by_location(int(pk), 999999999)