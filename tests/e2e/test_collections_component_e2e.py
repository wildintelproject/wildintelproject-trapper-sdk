"""
End-to-end tests for CollectionsComponent against a real Trapper server.

Requires environment variables:
    WILDINTEL_BASE_URL, WILDINTEL_ACCESS_TOKEN, WILDINTEL_SMOKE_ENABLED=1

Optional:
    WILDINTEL_COLLECTION_PK  — pk of an existing collection (for find/resources tests)
    WILDINTEL_RESOURCE_PK    — pk of an existing resource within the collection
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.base_component_tests import ComponentE2ETestBase
from trapper_client.api_query import APIQuery
from trapper_client.components.collections import CollectionsComponent
from trapper_client.schemas import Collection, PaginatedResult, Resource


# ── tests heredados ───────────────────────────────────────────────────────────

class TestCollectionsComponentE2E(ComponentE2ETestBase):
    component_class = CollectionsComponent
    schema = Collection
    export_schema = Collection
    env_pk_var = "WILDINTEL_COLLECTION_PK"


# ── helpers ───────────────────────────────────────────────────────────────────

def _collection_pk() -> str:
    return os.getenv("WILDINTEL_COLLECTION_PK", "").strip()


def _resource_pk() -> str:
    return os.getenv("WILDINTEL_RESOURCE_PK", "").strip()


# ── resources sub-endpoint ────────────────────────────────────────────────────

class TestCollectionResourcesE2E:

    @pytest.fixture(scope="class")
    def component(self, real_api_base):
        return CollectionsComponent(real_api_base)



# ── ondemand sub-endpoint ─────────────────────────────────────────────────────

@pytest.mark.usefixtures("v1_only")
class TestCollectionOndemandE2E:

    @pytest.fixture(scope="class")
    def component(self, real_api_base):
        return CollectionsComponent(real_api_base)

    @pytest.mark.e2e
    def test_where_ondemand_returns_api_query(self, component):
        """where_ondemand() devuelve un APIQuery."""
        assert isinstance(component.where_ondemand(), APIQuery)

    @pytest.mark.e2e
    def test_where_ondemand_iterates_collection_instances(self, component):
        """Iterar where_ondemand() devuelve instancias de Collection."""
        items = []
        for col in component.where_ondemand(page_size=10):
            items.append(col)
            if len(items) >= 5:
                break

        if not items:
            pytest.skip("No ondemand collections available for this user")

        assert all(isinstance(col, Collection) for col in items)

    @pytest.mark.e2e
    def test_get_ondemand_returns_paginated_result(self, component):
        """get_ondemand() devuelve PaginatedResult."""
        result = component.get_ondemand(page_size=5)

        assert isinstance(result, PaginatedResult)
        assert result.pagination.page == 1

    @pytest.mark.e2e
    def test_get_ondemand_returns_collection_instances(self, component):
        """get_ondemand() devuelve instancias de Collection."""
        result = component.get_ondemand(page_size=5)

        if not result.results:
            pytest.skip("No ondemand collections available for this user")

        assert all(isinstance(col, Collection) for col in result.results)

    @pytest.mark.e2e
    def test_get_all_ondemand_count_matches_pagination(self, component):
        """get_all_ondemand() devuelve tantos items como indica pagination.count."""
        result = component.get_all_ondemand(page_size=50)
        assert len(result.results) == result.pagination.count

    @pytest.mark.e2e
    def test_find_ondemand_returns_collection(self, component):
        """find_ondemand() devuelve instancia de Collection."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        if not component.get_ondemand(page_size=1).results:
            pytest.skip("no on-demand collections on this server")
        result = component.find_ondemand(int(pk))

        assert isinstance(result, Collection)
        assert result.pk == int(pk)


# ── map sub-endpoint ──────────────────────────────────────────────────────────

class TestCollectionMapE2E:

    @pytest.fixture(scope="class")
    def component(self, real_api_base):
        return CollectionsComponent(real_api_base)

    @pytest.mark.e2e
    def test_where_map_returns_api_query(self, component):
        """where_map() devuelve un APIQuery."""
        assert isinstance(component.where_map(), APIQuery)

    @pytest.mark.e2e
    def test_where_map_iterates_collection_instances(self, component):
        """Iterar where_map() devuelve instancias de Collection."""
        items = []
        for col in component.where_map(page_size=10):
            items.append(col)
            if len(items) >= 5:
                break

        if not items:
            pytest.skip("No map collections available for this user")

        assert all(isinstance(col, Collection) for col in items)

    @pytest.mark.e2e
    def test_get_map_returns_paginated_result(self, component):
        """get_map() devuelve PaginatedResult."""
        result = component.get_map(page_size=5)

        assert isinstance(result, PaginatedResult)

    @pytest.mark.e2e
    def test_get_map_returns_collection_instances(self, component):
        """get_map() devuelve instancias de Collection."""
        result = component.get_map(page_size=5)

        if not result.results:
            pytest.skip("No map collections available for this user")

        assert all(isinstance(col, Collection) for col in result.results)

    @pytest.mark.e2e
    def test_get_all_map_count_matches_pagination(self, component):
        """get_all_map() devuelve tantos items como indica pagination.count."""
        result = component.get_all_map(page_size=50)
        assert len(result.results) == result.pagination.count

    @pytest.mark.e2e
    def test_find_map_returns_collection(self, component):
        """find_map() devuelve instancia de Collection."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        result = component.find_map(int(pk))

        assert isinstance(result, Collection)


# ── append sub-endpoint ───────────────────────────────────────────────────────

class TestCollectionAppendE2E:

    @pytest.fixture(scope="class")
    def component(self, real_api_base):
        return CollectionsComponent(real_api_base)

    @pytest.mark.e2e
    def test_where_append_returns_api_query(self, component):
        """where_append() devuelve un APIQuery."""
        assert isinstance(component.where_append(), APIQuery)

    @pytest.mark.e2e
    def test_where_append_iterates_collection_instances(self, component):
        """Iterar where_append() devuelve instancias de Collection."""
        items = []
        for col in component.where_append(page_size=10):
            items.append(col)
            if len(items) >= 5:
                break

        if not items:
            pytest.skip("No append collections available for this user")

        assert all(isinstance(col, Collection) for col in items)

    @pytest.mark.e2e
    def test_get_append_returns_paginated_result(self, component):
        """get_append() devuelve PaginatedResult."""
        result = component.get_append(page_size=5)

        assert isinstance(result, PaginatedResult)

    @pytest.mark.e2e
    def test_get_append_returns_collection_instances(self, component):
        """get_append() devuelve instancias de Collection."""
        result = component.get_append(page_size=5)

        if not result.results:
            pytest.skip("No append collections available for this user")

        assert all(isinstance(col, Collection) for col in result.results)

    @pytest.mark.e2e
    def test_get_all_append_count_matches_pagination(self, component):
        """get_all_append() devuelve tantos items como indica pagination.count."""
        result = component.get_all_append(page_size=50)
        assert len(result.results) == result.pagination.count

    @pytest.mark.e2e
    def test_find_append_returns_collection(self, component):
        """find_append() devuelve instancia de Collection."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        result = component.find_append(int(pk))

        assert isinstance(result, Collection)

# ── list filters ──────────────────────────────────────────────────────────────

class TestCollectionFiltersE2E:

    @pytest.fixture(scope="class")
    def component(self, real_api_base):
        return CollectionsComponent(real_api_base)

    @staticmethod
    def count(component, **filters) -> int:
        return component.get(page_size=1, **filters).pagination.count

    @pytest.mark.e2e
    def test_pk_as_list_or_string_filters_the_same(self, component):
        """``pk=[a, b]`` used to keep one collection; every spelling gives the same result now."""
        pks = [c.pk for c in component.where(page_size=50)][:2]
        if len(pks) < 2:
            pytest.skip("Fewer than two collections on this server")
        assert self.count(component, pk=pks) == 2
        assert self.count(component, pk=",".join(map(str, pks))) == 2
        assert self.count(component, pk=tuple(pks)) == 2

    @pytest.mark.e2e
    def test_status_in_any_case_is_the_status_trapper_stores(self, component):
        """``status="private"`` was an empty result; it is the same as ``"Private"`` now."""
        from trapper_client import CollectionStatus

        everything = list(component.where(page_size=50))
        if not everything:
            pytest.skip("No collections on this server")
        status = everything[0].status
        expected = sum(1 for c in everything if c.status == status)
        assert expected >= 1
        assert self.count(component, status=status) == expected
        assert self.count(component, status=status.lower()) == expected
        assert self.count(component, status=CollectionStatus.parse(status)) == expected

    @pytest.mark.e2e
    def test_an_unknown_status_is_refused_not_an_empty_result(self, component):
        with pytest.raises(ValueError, match="OnDemand"):
            component.get(status="Bogus")

    @pytest.mark.e2e
    def test_unknown_filters_warn_and_known_ones_do_not(self, component):
        if getattr(component.client, "api_flavor", None) == "ninja":
            pytest.skip("the filters of the new API are not listed yet: nothing is warned about there")
        import warnings

        from trapper_client import err

        with warnings.catch_warnings():
            warnings.simplefilter("error", err.UnknownFilterWarning)
            total = self.count(component)
            assert self.count(component, name="zzz-no-such-collection") == 0
        with pytest.warns(err.UnknownFilterWarning):
            ignored = component.get(page_size=1, ordering="-pk", description="x")
        assert ignored.pagination.count == total
