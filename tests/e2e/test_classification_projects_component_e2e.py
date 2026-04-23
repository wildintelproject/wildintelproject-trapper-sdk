"""
End-to-end tests for ClassificationProjectsComponent against a real Trapper server.

Requires environment variables:
    WILDINTEL_BASE_URL, WILDINTEL_ACCESS_TOKEN, WILDINTEL_SMOKE_ENABLED=1

Optional:
    WILDINTEL_CLASSIFICATION_PROJECT_PK   — pk of an existing classification project
    WILDINTEL_CLASSIFICATION_LINK_PK      — pk of an existing project-collection link
    WILDINTEL_CLASSIFICATION_COLLECTION_PK — collection pk linked to the project
"""
from __future__ import annotations

import os

import pytest

from tests.base_component_tests import ComponentE2ETestBase
from trapper_client.api_query import APIQuery
from trapper_client.components.classification_projects import ClassificationProjectsComponent
from trapper_client.schemas import ClassificationProject, ClassificationProjectCollection, PaginatedResult


# ── tests heredados ───────────────────────────────────────────────────────────

class TestClassificationProjectsComponentE2E(ComponentE2ETestBase):
    component_class = ClassificationProjectsComponent
    schema = ClassificationProject
    export_schema = ClassificationProject
    env_pk_var = "WILDINTEL_CLASSIFICATION_PROJECT_PK"


# ── helpers ───────────────────────────────────────────────────────────────────

def _project_pk() -> str:
    return os.getenv("WILDINTEL_CLASSIFICATION_PROJECT_PK", "").strip()


def _link_pk() -> str:
    return os.getenv("WILDINTEL_CLASSIFICATION_LINK_PK", "").strip()


def _collection_pk() -> str:
    return os.getenv("WILDINTEL_CLASSIFICATION_COLLECTION_PK", "").strip()


# ── tests específicos de colecciones ─────────────────────────────────────────

class TestClassificationProjectCollectionsE2E:

    @pytest.fixture(scope="class")
    def component(self, real_api_base):
        return ClassificationProjectsComponent(real_api_base)

    # ── get_project_collections ───────────────────────────────────────────────

    @pytest.mark.e2e
    def test_get_project_collections_returns_paginated_result(self, component):
        """get_project_collections() devuelve PaginatedResult."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.get_project_collections(project_pk=int(pk), page_size=5)

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results, list)

    @pytest.mark.e2e
    def test_get_project_collections_returns_correct_schema(self, component):
        """get_project_collections() devuelve instancias de ClassificationProjectCollection."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.get_project_collections(project_pk=int(pk), page_size=5)

        if not result.results:
            pytest.skip("No collections available for this project")

        assert all(isinstance(col, ClassificationProjectCollection) for col in result.results)

    @pytest.mark.e2e
    def test_get_project_collections_page_size_respected(self, component):
        """get_project_collections() respeta el page_size solicitado."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.get_project_collections(project_pk=int(pk), page_size=3)

        assert len(result.results) <= 3

    @pytest.mark.e2e
    def test_get_project_collections_validate_false_returns_models(self, component):
        """get_project_collections() con validate=False devuelve modelos sin validar."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.get_project_collections(project_pk=int(pk), validate=False)

        if not result.results:
            pytest.skip("No collections available for this project")

        assert all(isinstance(col, ClassificationProjectCollection) for col in result.results)

    # ── get_all_project_collections ───────────────────────────────────────────

    @pytest.mark.e2e
    def test_get_all_project_collections_count_matches_pagination(self, component):
        """get_all_project_collections() devuelve tantos items como indica pagination.count."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.get_all_project_collections(project_pk=int(pk), page_size=50)

        assert len(result.results) == result.pagination.count

    @pytest.mark.e2e
    def test_get_all_project_collections_returns_correct_schema(self, component):
        """get_all_project_collections() devuelve instancias de ClassificationProjectCollection."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.get_all_project_collections(project_pk=int(pk), page_size=50)

        for col in result.results:
            assert isinstance(col, ClassificationProjectCollection)

    @pytest.mark.e2e
    def test_get_all_project_collections_no_duplicate_pks(self, component):
        """get_all_project_collections() no devuelve items duplicados entre páginas."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.get_all_project_collections(project_pk=int(pk), page_size=10)

        if not result.results:
            pytest.skip("No collections available for this project")

        pks = [col.pk for col in result.results]
        assert len(pks) == len(set(pks))

    # ── where_project_collections ─────────────────────────────────────────────

    @pytest.mark.e2e
    def test_where_project_collections_returns_api_query(self, component):
        """where_project_collections() devuelve un APIQuery."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        assert isinstance(component.where_project_collections(project_pk=int(pk)), APIQuery)

    @pytest.mark.e2e
    def test_where_project_collections_iterates_correct_schema(self, component):
        """Iterar where_project_collections() devuelve instancias de ClassificationProjectCollection."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        items = []
        for col in component.where_project_collections(project_pk=int(pk), page_size=10):
            items.append(col)
            if len(items) >= 5:
                break

        if not items:
            pytest.skip("No collections available for this project")

        assert all(isinstance(col, ClassificationProjectCollection) for col in items)

    @pytest.mark.e2e
    def test_where_project_collections_context_manager_exhausts_on_exit(self, component):
        """where_project_collections() como context manager queda exhausto al salir."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        with component.where_project_collections(project_pk=int(pk), page_size=5) as query:
            next(query, None)

        assert query._exhausted is True

    # ── find_project_collection ───────────────────────────────────────────────

    @pytest.mark.e2e
    def test_find_project_collection_returns_correct_schema(self, component):
        """find_project_collection() devuelve instancia de ClassificationProjectCollection."""
        project_pk = _project_pk()
        link_pk = _link_pk()
        if not project_pk or not link_pk:
            pytest.skip(
                "Set WILDINTEL_CLASSIFICATION_PROJECT_PK and "
                "WILDINTEL_CLASSIFICATION_LINK_PK to run this test"
            )

        result = component.find_project_collection(
            project_pk=int(project_pk),
            pk=int(link_pk),
        )

        assert isinstance(result, ClassificationProjectCollection)
        assert result.pk == int(link_pk)

    @pytest.mark.e2e
    def test_find_project_collection_validate_false_returns_model(self, component):
        """find_project_collection() con validate=False devuelve modelo sin validar."""
        project_pk = _project_pk()
        link_pk = _link_pk()
        if not project_pk or not link_pk:
            pytest.skip(
                "Set WILDINTEL_CLASSIFICATION_PROJECT_PK and "
                "WILDINTEL_CLASSIFICATION_LINK_PK to run this test"
            )

        result = component.find_project_collection(
            project_pk=int(project_pk),
            pk=int(link_pk),
            validate=False,
        )

        assert isinstance(result, ClassificationProjectCollection)

    @pytest.mark.e2e
    def test_find_project_collection_nonexistent_raises(self, component):
        """find_project_collection() lanza excepción para pk inexistente."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        with pytest.raises(Exception):
            component.find_project_collection(project_pk=int(pk), pk=999999999)

    # ── find_collection_in_project ────────────────────────────────────────────

    @pytest.mark.e2e
    def test_find_collection_in_project_returns_link_pk_when_found(self, component):
        """find_collection_in_project() devuelve el pk del link cuando la colección existe."""
        project_pk = _project_pk()
        collection_pk = _collection_pk()
        if not project_pk or not collection_pk:
            pytest.skip(
                "Set WILDINTEL_CLASSIFICATION_PROJECT_PK and "
                "WILDINTEL_CLASSIFICATION_COLLECTION_PK to run this test"
            )

        result = component.find_collection_in_project(
            project_pk=int(project_pk),
            collection_pk=int(collection_pk),
        )

        assert isinstance(result, int)

    @pytest.mark.e2e
    def test_find_collection_in_project_returns_none_when_not_found(self, component):
        """find_collection_in_project() devuelve None para una colección que no existe en el proyecto."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK to run this test")

        result = component.find_collection_in_project(
            project_pk=int(pk),
            collection_pk=999999999,
        )

        assert result is None