"""
Unit tests for ResearchProjectsComponent.

Covers both inherited TrapperComponent behaviour and the project-collections
specific methods.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import ComponentUnitTestBase, paginated_response
from trapper_client import err
from trapper_client.api_query import APIQuery
from trapper_client.components.research_projects import ResearchProjectsComponent
from trapper_client.enums import BaitUse, SamplingDesign
from trapper_client.schemas import (
    PaginatedResult,
    ResearchProject,
    ResearchProjectCollection,
    ResearchProjectCreate,
)


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

# ── create() ─────────────────────────────────────────────────────────────────

FORM_PAGE = """
<form>
<select name="project_roles-0-user"><option value="">---</option>
<option value="4" selected>rp_staff</option><option value="5">rp_user</option></select>
<select name="project_roles-0-name"><option value="1" selected>Admin</option>
<option value="2">Expert</option></select>
</form>
"""


REQUEST = ResearchProjectCreate(name="N", acronym="ABC")


class TestCreate:
    """create() simulates the classic ``research/project/create/`` web form (v1 only)."""

    @pytest.fixture
    def client(self):
        c = MagicMock()
        c.server_version = "v1"
        c.base_url = "https://trapper.example"
        c._web_client.get.return_value = MagicMock(status_code=200, text=FORM_PAGE)
        c.session_post_multipart.return_value = MagicMock(
            status_code=302, headers={"location": "/research/project/list/"}
        )
        return c

    @pytest.fixture
    def component(self, client):
        comp = ResearchProjectsComponent(client)
        comp.where = MagicMock(return_value=iter([ResearchProject(pk=9, name="N", acronym="ABC")]))
        return comp

    def test_returns_the_created_project(self, component):
        project = component.create(REQUEST)
        assert project.pk == 9
        component.where.assert_called_once_with(acronym="ABC", page_size=5)

    def test_posts_the_form_with_the_owner_as_admin(self, component, client):
        component.create(ResearchProjectCreate(
            name="My project", acronym="MYP", sampling_design=SamplingDesign.TARGETED,
            sensor_method=2, animal_types="marked", bait_use=BaitUse.FOOD, event_interval=30,
            keywords=["a", " b ", ""], abstract="abs",
        ))
        endpoint = client.session_post_multipart.call_args.args[0]
        data = client.session_post_multipart.call_args.kwargs["data"]
        assert endpoint == "research/project/create/"
        assert data["name"] == "My project" and data["acronym"] == "MYP"
        assert (data["sampling_design"], data["sensor_method"]) == (5, 2)
        assert (data["animal_types"], data["bait_use"], data["event_interval"]) == (2, 3, 30)
        assert data["keywords"] == '"a", "b"'
        assert data["abstract"] == "abs" and data["methods"] == "" and data["description"] == ""
        assert data["project_roles-TOTAL_FORMS"] == 1
        assert data["project_roles-INITIAL_FORMS"] == 0
        assert data["project_roles-0-user"] == "4"
        assert data["project_roles-0-name"] == "1"

    def test_only_takes_the_model(self, component, client):
        with pytest.raises(TypeError, match="takes a ResearchProjectCreate, not dict"):
            component.create({"name": "N", "acronym": "ABC"})
        client.session_post_multipart.assert_not_called()

    def test_a_dict_is_turned_into_the_model_by_the_caller(self, component, client):
        component.create(ResearchProjectCreate.model_validate({"name": "N", "acronym": "ABC", "bait_use": "scent"}))
        assert client.session_post_multipart.call_args.kwargs["data"]["bait_use"] == 2

    def test_none_when_the_project_is_not_visible_yet(self, component):
        component.where = MagicMock(return_value=iter([]))
        assert component.create(REQUEST) is None

    def test_rejected_form_raises_with_the_server_message(self, component, client):
        client.session_post_multipart.return_value = MagicMock(status_code=200, text="<html/>")
        client._extract_html_error_text.return_value = "acronym: already exists."
        with pytest.raises(err.APIError, match="status 200.*acronym: already exists"):
            component.create(REQUEST)

    def test_rejected_form_returns_none_without_raise_on_error(self, component, client):
        client.session_post_multipart.return_value = MagicMock(status_code=200, text="<html/>")
        client._extract_html_error_text.return_value = "x"
        assert component.create(REQUEST, raise_on_error=False) is None

    def test_redirect_to_login_is_not_success(self, component, client):
        client.session_post_multipart.return_value = MagicMock(
            status_code=302, headers={"location": "/account/login/?next=/research/"}
        )
        with pytest.raises(err.APIError, match="login page"):
            component.create(REQUEST)

    def test_form_page_not_available(self, component, client):
        client._web_client.get.return_value = MagicMock(status_code=403, text="")
        with pytest.raises(err.APIError, match="status 403"):
            component.create(REQUEST)

    def test_form_without_preselected_owner(self, component, client):
        client._web_client.get.return_value = MagicMock(status_code=200, text="<form></form>")
        with pytest.raises(err.APIError, match="Trapper changed the form"):
            component.create(REQUEST)

    def test_not_available_on_v2(self, component, client):
        client.server_version = "v2"
        with pytest.raises(err.UnsupportedVersionError):
            component.create(REQUEST)
        client.session_post_multipart.assert_not_called()


class TestResearchProjectCreate:
    """The request model: what ``create()`` validates before anything is sent."""

    def test_defaults_are_the_first_choice_of_each_field(self):
        r = ResearchProjectCreate(name="N", acronym="ABC")
        assert (r.sampling_design, r.sensor_method) == (SamplingDesign.SIMPLE_RANDOM, 1)
        assert (r.animal_types, r.bait_use, r.event_interval) == (1, BaitUse.NONE, 0)
        assert r.keywords == [] and r.abstract is None

    def test_choices_take_a_member_a_number_or_a_label(self):
        for value in (SamplingDesign.TARGETED, 5, "targeted"):
            assert ResearchProjectCreate(name="N", acronym="ABC", sampling_design=value).sampling_design is SamplingDesign.TARGETED

    def test_text_is_trimmed_and_keywords_cleaned(self):
        r = ResearchProjectCreate(name="  Doñana ", acronym=" DON ", keywords=[" a ", "", "b"])
        assert (r.name, r.acronym, r.keywords) == ("Doñana", "DON", ["a", "b"])

    @pytest.mark.parametrize("kwargs", [
        {"name": "  ", "acronym": "ABC"},
        {"name": "x" * 256, "acronym": "ABC"},
        {"name": "N", "acronym": "abcdefghijk"},
        {"name": "N", "acronym": "ABC", "sampling_design": 7},
        {"name": "N", "acronym": "ABC", "sensor_method": True},
        {"name": "N", "acronym": "ABC", "bait_use": SamplingDesign.TARGETED},
        {"name": "N", "acronym": "ABC", "event_interval": -1},
        {"name": "N", "acronym": "ABC", "abstract": "x" * 2001},
        {"name": "N", "acronym": "ABC", "keywords": ['say "hi"']},
        {"name": "N", "acronym": "ABC", "unknown_field": 1},
    ])
    def test_invalid_values_are_rejected(self, kwargs):
        with pytest.raises(ValueError):
            ResearchProjectCreate(**kwargs)

    def test_to_form_gives_the_numbers_trapper_stores(self):
        form = ResearchProjectCreate(
            name="N", acronym="ABC", sampling_design="opportunistic", bait_use="acoustic",
            keywords=["x", "y"], description="d",
        ).to_form()
        assert form["sampling_design"] == 6 and form["bait_use"] == 5
        assert type(form["sampling_design"]) is int
        assert form["keywords"] == '"x", "y"' and form["description"] == "d" and form["abstract"] == ""

    def test_keywords_travel_quoted_so_that_spaces_and_commas_stay_inside(self):
        form = ResearchProjectCreate(name="N", acronym="ABC", keywords=["camera trap", "a, b"]).to_form()
        assert form["keywords"] == '"camera trap", "a, b"'

    def test_a_single_keyword_with_a_space_is_still_one_keyword(self):
        # unquoted, Trapper splits "camera trap" into two keywords when it is the only one
        assert ResearchProjectCreate(name="N", acronym="ABC", keywords=["camera trap"]).to_form()["keywords"] == '"camera trap"'

    def test_no_keywords_sends_nothing(self):
        assert ResearchProjectCreate(name="N", acronym="ABC").to_form()["keywords"] == ""
