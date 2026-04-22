"""
End-to-end tests for ResearchProjectsComponent against a real Trapper server.

Requires environment variables:
    WILDINTEL_BASE_URL, WILDINTEL_ACCESS_TOKEN, WILDINTEL_SMOKE_ENABLED=1

Optional:
    WILDINTEL_PROJECT_PK     — pk of an existing research project
    WILDINTEL_COLLECTION_PK  — pk of an existing project-collection link
"""
from __future__ import annotations

import os

import pytest

from tests.base_component_tests import ComponentE2ETestBase
from trapper_client.api_query import APIQuery
from trapper_client.components.research_projects import ResearchProjectsComponent
from trapper_client.schemas import PaginatedResult, ResearchProject, ResearchProjectCollection


# ── tests heredados ───────────────────────────────────────────────────────────

class TestResearchProjectsComponentE2E(ComponentE2ETestBase):
    component_class = ResearchProjectsComponent
    schema = ResearchProject
    export_schema = ResearchProject     # sin export_schema propio usa schema
    env_pk_var = "WILDINTEL_PROJECT_PK"


# ── tests específicos de colecciones ─────────────────────────────────────────

@pytest.fixture(scope="module")
def projects(real_api_base):
    return ResearchProjectsComponent(real_api_base)


def _project_pk() -> str:
    return os.getenv("WILDINTEL_PROJECT_PK", "").strip()


def _collection_pk() -> str:
    return os.getenv("WILDINTEL_COLLECTION_PK", "").strip()


class TestResearchProjectCollectionsE2E:

    @pytest.fixture(scope="class")
    def projects(self, real_api_base):
        return ResearchProjectsComponent(real_api_base)

    # ── get_project_collections ───────────────────────────────────────────────

    @pytest.mark.e2e
    def test_get_project_collections_returns_paginated_result(self, projects):
        """get_project_collections() devuelve PaginatedResult."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_PROJECT_PK to run this test")

        result = projects.get_project_collections(project_pk=int(pk), page_size=5)

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results, list)

    @pytest.mark.e2e
    def test_get_project_collections_returns_correct_schema(self, projects):
        """get_project_collections() devuelve instancias de ResearchProjectCollection."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_PROJECT_PK to run this test")

        result = projects.get_project_collections(project_pk=int(pk), page_size=5)

        if not result.results:
            pytest.skip("No collections available for this project")

        assert all(isinstance(col, ResearchProjectCollection) for col in result.results)

    @pytest.mark.e2e
    def test_get_project_collections_page_size_respected(self, projects):
        """get_project_collections() respeta el page_size solicitado."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_PROJECT_PK to run this test")

        result = projects.get_project_collections(project_pk=int(pk), page_size=3)

        assert len(result.results) <= 3

    @pytest.mark.e2e
    def test_get_project_collections_validate_false_returns_models(self, projects):
        """get_project_collections() con validate=False devuelve modelos sin validar."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_PROJECT_PK to run this test")

        result = projects.get_project_collections(project_pk=int(pk), validate=False)

        if not result.results:
            pytest.skip("No collections available for this project")

        assert all(isinstance(col, ResearchProjectCollection) for col in result.results)

    # ── get_all_project_collections ───────────────────────────────────────────

    @pytest.mark.e2e
    def test_get_all_project_collections_count_matches_pagination(self, projects):
        """get_all_project_collections() devuelve tantos items como indica pagination.count."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_PROJECT_PK to run this test")

        result = projects.get_all_project_collections(project_pk=int(pk), page_size=50)

        assert len(result.results) == result.pagination.count

    @pytest.mark.e2e
    def test_get_all_project_collections_returns_correct_schema(self, projects):
        """get_all_project_collections() devuelve instancias de ResearchProjectCollection."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_PROJECT_PK to run this test")

        result = projects.get_all_project_collections(project_pk=int(pk), page_size=50)

        for col in result.results:
            assert isinstance(col, ResearchProjectCollection)

    # ── where_project_collections ─────────────────────────────────────────────

    @pytest.mark.e2e
    def test_where_project_collections_returns_api_query(self, projects):
        """where_project_collections() devuelve un APIQuery."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_PROJECT_PK to run this test")

        result = projects.where_project_collections(project_pk=int(pk))

        assert isinstance(result, APIQuery)

    @pytest.mark.e2e
    def test_where_project_collections_iterates_and_returns_correct_schema(self, projects):
        """Iterar where_project_collections() devuelve instancias de ResearchProjectCollection."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_PROJECT_PK to run this test")

        items = []
        for col in projects.where_project_collections(project_pk=int(pk), page_size=10):
            items.append(col)
            if len(items) >= 5:
                break

        if not items:
            pytest.skip("No collections available for this project")

        assert all(isinstance(col, ResearchProjectCollection) for col in items)

    @pytest.mark.e2e
    def test_where_project_collections_exhausts_on_context_manager_exit(self, projects):
        """where_project_collections() como context manager queda exhausto al salir."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_PROJECT_PK to run this test")

        with projects.where_project_collections(project_pk=int(pk), page_size=5) as query:
            next(query, None)

        assert query._exhausted is True

    # ── find_project_collection ───────────────────────────────────────────────

    @pytest.mark.e2e
    def test_find_project_collection_returns_correct_schema(self, projects):
        """find_project_collection() devuelve instancia de ResearchProjectCollection."""
        project_pk = _project_pk()
        collection_pk = _collection_pk()
        if not project_pk or not collection_pk:
            pytest.skip("Set WILDINTEL_PROJECT_PK and WILDINTEL_COLLECTION_PK to run this test")

        result = projects.find_project_collection(
            project_pk=int(project_pk),
            pk=int(collection_pk),
        )

        assert isinstance(result, ResearchProjectCollection)
        assert result.pk == int(collection_pk)

    @pytest.mark.e2e
    def test_find_project_collection_validate_false_returns_model(self, projects):
        """find_project_collection() con validate=False devuelve modelo sin validar."""
        project_pk = _project_pk()
        collection_pk = _collection_pk()
        if not project_pk or not collection_pk:
            pytest.skip("Set WILDINTEL_PROJECT_PK and WILDINTEL_COLLECTION_PK to run this test")

        result = projects.find_project_collection(
            project_pk=int(project_pk),
            pk=int(collection_pk),
            validate=False,
        )

        assert isinstance(result, ResearchProjectCollection)

    @pytest.mark.e2e
    def test_find_project_collection_nonexistent_raises(self, projects):
        """find_project_collection() lanza excepción para pk que no existe."""
        pk = _project_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_PROJECT_PK to run this test")

        with pytest.raises(Exception):
            projects.find_project_collection(project_pk=int(pk), pk=999999999)