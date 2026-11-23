"""
Unit tests for ClassificationProjectsComponent.

Covers inherited TrapperComponent behaviour plus the project-collections
specific methods.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import ComponentUnitTestBase, paginated_response
from trapper_client import err
from trapper_client.api_query import APIQuery
from trapper_client.enums import ClassificationProjectRoleType
from trapper_client.components.classification_projects import ClassificationProjectsComponent
from trapper_client.schemas import (
    ClassificationProject,
    ClassificationProjectCollection,
    ClassificationProjectCreate,
    ClassificationProjectMember,
    ClassifiedResource,
    Classificator,
    ResearchProject,
    PaginatedResult,
    User,
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
        assert isinstance(result.results[0], ClassifiedResource)

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
        """where_collection_resources() usa ClassifiedResource como schema."""
        query = component.where_collection_resources(collection_pk=LINK_PK)
        assert query.schema is ClassifiedResource

    # ── get_all_collection_resources ──────────────────────────────────────────

    def test_get_all_collection_resources_returns_paginated_result(self, component, client):
        """get_all_collection_resources() devuelve PaginatedResult con todos los items."""
        client.get_all.return_value = paginated_response([VALID_RESOURCE])

        result = component.get_all_collection_resources(collection_pk=LINK_PK)

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], ClassifiedResource)

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
        """get_collection_resources_around() devuelve items tipados como ClassifiedResource."""
        client.get.return_value = paginated_response([VALID_RESOURCE])

        result = component.get_collection_resources_around(collection_pk=LINK_PK, resource_pk=4831)

        assert isinstance(result, PaginatedResult)
        assert isinstance(result.results[0], ClassifiedResource)

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


# ── write access: create / add_collections / remove_collection ───────────────

FORM_PAGE = """
<select name="classification_project_roles-0-user"><option value="">---</option>
<option value="4" selected>rp_staff</option></select>
<select name="classification_project_roles-0-name"><option value="1" selected>Admin</option></select>
"""


def _project(pk, name="Doñana", research_project="Host"):
    return ClassificationProject(**{**VALID_PROJECT, "pk": pk, "name": name, "research_project": research_project})


def _link(pk, collection_pk):
    return ClassificationProjectCollection(
        pk=pk, collection_pk=collection_pk, name=f"c{collection_pk}", status="OnDemand", is_active=True,
    )


class TestCreate:

    @pytest.fixture
    def client(self):
        c = MagicMock()
        c.server_version = "v1"
        c.base_url = "https://trapper.example"
        c._web_client.get.return_value = MagicMock(status_code=200, text=FORM_PAGE)
        c.session_post_multipart.return_value = MagicMock(
            status_code=302, headers={"location": "/media_classification/project/list/"}
        )
        return c

    @pytest.fixture
    def component(self, client):
        comp = ClassificationProjectsComponent(client)
        # before the POST: nothing called "Doñana"; after: the new project 7 (an older one, 3, stays)
        comp.where = MagicMock(side_effect=[iter([_project(3)]), iter([_project(3), _project(7)])])
        return comp

    def test_returns_the_new_project_not_a_namesake(self, component):
        project = component.create(ClassificationProjectCreate(name="Doñana", research_project=1, classificator=2))
        assert project.pk == 7

    def test_posts_the_form_with_the_owner_as_admin(self, component, client):
        component.create(ClassificationProjectCreate(name=" Doñana ", research_project=1, classificator=2))
        endpoint = client.session_post_multipart.call_args.args[0]
        data = client.session_post_multipart.call_args.kwargs["data"]
        assert endpoint == "media_classification/project/create/"
        assert (data["name"], data["research_project"], data["classificator"], data["status"]) == ("Doñana", 1, 2, 1)
        assert data["classification_project_roles-TOTAL_FORMS"] == 1
        assert data["classification_project_roles-0-user"] == "4"
        assert data["classification_project_roles-0-name"] == "1"

    def test_rejected_form_names_the_field(self, component, client):
        client.session_post_multipart.return_value = MagicMock(status_code=200, text="<html/>")
        client._extract_html_error_text.return_value = "classificator: Select a valid choice."
        with pytest.raises(err.APIError, match="classificator: Select a valid choice"):
            component.create(ClassificationProjectCreate(name="N", research_project=1, classificator=2))

    def test_rejected_form_returns_none_without_raise_on_error(self, component, client):
        client.session_post_multipart.return_value = MagicMock(status_code=200, text="<html/>")
        assert component.create(ClassificationProjectCreate(name="N", research_project=1, classificator=2), raise_on_error=False) is None

    def test_not_available_on_v2(self, component, client):
        client.server_version = "v2"
        with pytest.raises(err.UnsupportedVersionError):
            component.create(ClassificationProjectCreate(name="N", research_project=1, classificator=2))
        client.session_post_multipart.assert_not_called()

    def test_only_takes_the_model(self, component, client):
        with pytest.raises(TypeError, match="takes a ClassificationProjectCreate, not dict"):
            component.create({"name": "N", "research_project": 1, "classificator": 2})
        client.session_post_multipart.assert_not_called()

    @pytest.mark.parametrize("data", [
        {"name": " ", "research_project": 1, "classificator": 2},
        {"name": "N", "research_project": 0, "classificator": 2},
        {"name": "N", "research_project": 1, "classificator": -1},
        {"name": "N", "research_project": 1, "classificator": 2, "typo": 1},
        {"name": "N", "research_project": 1},
    ])
    def test_the_model_rejects_invalid_data_before_create_is_reached(self, data):
        with pytest.raises(ValueError):
            ClassificationProjectCreate.model_validate(data)


class TestAddAndRemoveCollections:

    @pytest.fixture
    def client(self):
        c = MagicMock()
        c.server_version = "v1"
        c.base_url = "https://trapper.example"
        c.session_post_multipart.return_value = MagicMock(
            status_code=200, json=MagicMock(return_value={"success": True, "msg": "ok"})
        )
        # research project "Host" is pk 10 and holds storage collections 1, 2 (links 4, 5)
        c.research_projects.where.return_value = [SimpleNamespace(pk=10, name="Host")]
        c.research_projects.where_project_collections.return_value = [
            MagicMock(pk=4, collection_pk=1), MagicMock(pk=5, collection_pk=2),
        ]
        return c

    @pytest.fixture
    def component(self, client):
        comp = ClassificationProjectsComponent(client)
        comp.find = MagicMock(return_value=_project(7))
        return comp

    def test_adds_only_the_missing_collections_by_their_research_links(self, component, client):
        component.where_project_collections = MagicMock(
            side_effect=[[_link(50, 1)], [_link(50, 1), _link(51, 2)]]
        )
        links = component.add_collections(7, [1, 2])
        data = client.session_post_multipart.call_args.kwargs["data"]
        assert client.session_post_multipart.call_args.args[0] == "media_classification/project/collection/add/"
        assert data == {"project": 7, "rproject": 10, "collections_pks": "5"}   # link 5, not storage 2
        assert [l.collection_pk for l in links] == [1, 2]

    def test_nothing_is_posted_when_all_are_already_there(self, component, client):
        component.where_project_collections = MagicMock(return_value=[_link(50, 1)])
        assert [l.pk for l in component.add_collections(7, [1])] == [50]
        client.session_post_multipart.assert_not_called()

    def test_a_collection_outside_the_research_project_is_refused(self, component, client):
        component.where_project_collections = MagicMock(return_value=[])
        with pytest.raises(ValueError, match=r"\[3\] are not in the research project 'Host'"):
            component.add_collections(7, [1, 3])
        client.session_post_multipart.assert_not_called()

    def test_the_servers_refusal_is_raised(self, component, client):
        component.where_project_collections = MagicMock(return_value=[])
        client.session_post_multipart.return_value = MagicMock(
            status_code=200, json=MagicMock(return_value={"success": False, "msg": "Nothing to process"})
        )
        with pytest.raises(err.APIError, match="Nothing to process"):
            component.add_collections(7, [1])

    def test_accepted_but_not_linked_is_an_error(self, component):
        component.where_project_collections = MagicMock(return_value=[])
        with pytest.raises(err.APIError, match="still not linked"):
            component.add_collections(7, [1])

    def test_empty_list_is_a_value_error(self, component):
        with pytest.raises(ValueError, match="empty"):
            component.add_collections(7, [])

    def test_remove_unlinks_through_the_delete_url(self, component, client):
        component.find_collection_in_project = MagicMock(side_effect=[50, None])
        assert component.remove_collection(7, 1) is True
        url = client._web_client.get.call_args.args[0]
        assert url == "https://trapper.example/media_classification/project/collection/delete/50/"

    def test_remove_a_collection_that_is_not_linked(self, component, client):
        component.find_collection_in_project = MagicMock(return_value=None)
        assert component.remove_collection(7, 1) is False
        client._web_client.get.assert_not_called()

    def test_remove_that_trapper_did_not_perform_raises(self, component):
        component.find_collection_in_project = MagicMock(return_value=50)   # still there afterwards
        with pytest.raises(err.APIError, match="may not be allowed"):
            component.remove_collection(7, 1)

    def test_not_available_on_v2(self, component, client):
        client.server_version = "v2"
        for call in (lambda: component.add_collections(7, [1]), lambda: component.remove_collection(7, 1)):
            with pytest.raises(err.UnsupportedVersionError):
                call()


class TestClassificationProjectCreateModel:

    def test_takes_the_objects_the_sdk_returns_or_their_primary_keys(self):
        rp = ResearchProject(pk=3, name="Host")
        clf = Classificator(pk=2, name="C", owner="o", updated_date="2026-01-01")
        by_object = ClassificationProjectCreate(name="N", research_project=rp, classificator=clf)
        by_key = ClassificationProjectCreate(name="N", research_project=3, classificator=2)
        assert by_object.research_project == 3 and by_object.classificator == 2
        assert by_object.to_form() == by_key.to_form()

    def test_an_object_with_a_non_positive_pk_is_rejected(self):
        with pytest.raises(ValueError, match="positive"):
            ClassificationProjectCreate(name="N", research_project=ResearchProject(pk=0), classificator=2)


class TestMembers:
    """Members and roles: the role rows after the creator's in the form."""

    @pytest.fixture
    def client(self):
        c = MagicMock()
        c.server_version = "v1"
        c.base_url = "https://trapper.example"
        c._web_client.get.return_value = MagicMock(status_code=200, text=FORM_PAGE)
        c.session_post_multipart.return_value = MagicMock(
            status_code=302, headers={"location": "/media_classification/project/list/"}
        )
        return c

    @pytest.fixture
    def component(self, client):
        comp = ClassificationProjectsComponent(client)
        comp.where = MagicMock(side_effect=[iter([]), iter([_project(7)])])
        return comp

    def test_the_members_are_posted_after_the_creator(self, component, client):
        component.create(ClassificationProjectCreate(name="Doñana", research_project=1, classificator=2, members=[
            ClassificationProjectMember(user=User(pk=7, username="ana"), role="expert"),
            ClassificationProjectMember(user=9, role=ClassificationProjectRoleType.CITIZEN),
        ]))
        data = client.session_post_multipart.call_args.kwargs["data"]
        assert data["classification_project_roles-TOTAL_FORMS"] == 3
        assert (data["classification_project_roles-0-user"], data["classification_project_roles-0-name"]) == ("4", "1")
        assert (data["classification_project_roles-1-user"], data["classification_project_roles-1-name"]) == (7, 2)
        assert (data["classification_project_roles-2-user"], data["classification_project_roles-2-name"]) == (9, 5)

    def test_without_members_only_the_creator_is_posted(self, component, client):
        component.create(ClassificationProjectCreate(name="Doñana", research_project=1, classificator=2))
        data = client.session_post_multipart.call_args.kwargs["data"]
        assert data["classification_project_roles-TOTAL_FORMS"] == 1

    def test_the_creator_cannot_be_listed_as_a_member(self, component, client):
        with pytest.raises(ValueError, match="already its administrator"):
            component.create(ClassificationProjectCreate(
                name="Doñana", research_project=1, classificator=2,
                members=[ClassificationProjectMember(user=4, role="expert")],
            ))
        client.session_post_multipart.assert_not_called()


class TestClassificationProjectMember:

    def test_takes_a_user_object_or_a_primary_key_and_the_five_roles(self):
        assert ClassificationProjectMember(user=User(pk=7, username="ana"), role="Error proof").role is \
            ClassificationProjectRoleType.ERROR_PROOF
        assert ClassificationProjectMember(user=7, role=5).role is ClassificationProjectRoleType.CITIZEN

    @pytest.mark.parametrize("kwargs", [
        {"user": 0, "role": "expert"},
        {"user": 7, "role": "boss"},
        {"user": 7, "role": 6},
        {"user": 7},
        {"user": 7, "role": "expert", "extra": 1},
    ])
    def test_invalid_members_are_rejected(self, kwargs):
        with pytest.raises(ValueError):
            ClassificationProjectMember(**kwargs)

    def test_a_user_cannot_appear_twice(self):
        with pytest.raises(ValueError, match=r"users \[7\] appear more than once"):
            ClassificationProjectCreate(name="N", research_project=1, classificator=2, members=[
                ClassificationProjectMember(user=7, role="expert"),
                ClassificationProjectMember(user=7, role="collaborator"),
            ])

    def test_role_rows(self):
        c = ClassificationProjectCreate(name="N", research_project=1, classificator=2,
                                        members=[ClassificationProjectMember(user=7, role="collaborator")])
        assert c.role_rows() == [(7, 3)]
