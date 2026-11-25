"""
A primary-key parameter also takes the SDK object it stands for (issue #75). Mocked: no server needed.
"""
from __future__ import annotations

import inspect
from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import paginated_response
from trapper_client import components as C
from trapper_client._pk import as_pk, takes_pk
from trapper_client.schemas import (
    ClassificationProject,
    ClassificationProjectCollection,
    Collection,
    Deployment,
    Location,
    ResearchProject,
    Resource,
)


def _cp(pk=2):
    return ClassificationProject.model_construct(pk=pk, name="p")


class TestAsPk:

    @pytest.mark.parametrize("value, pk", [(7, 7), ("7", 7), (" 7 ", 7), (None, None)])
    def test_numbers(self, value, pk):
        assert as_pk(value, ClassificationProject, "project_pk") == pk

    def test_the_object(self):
        assert as_pk(_cp(9), ClassificationProject, "project_pk") == 9

    def test_one_of_several_types(self):
        assert as_pk(Resource.model_construct(pk=4), (Resource, Location), "resource_pk") == 4

    @pytest.mark.parametrize("value", [True, 7.0, "abc", [7], {"pk": 7}])
    def test_anything_else_is_a_type_error(self, value):
        with pytest.raises(TypeError, match="project_pk takes a primary key"):
            as_pk(value, ClassificationProject, "project_pk")

    def test_an_object_of_another_type_is_a_type_error(self):
        with pytest.raises(TypeError, match="or a ClassificationProject, not Deployment"):
            as_pk(Deployment.model_construct(pk=3), ClassificationProject, "project_pk")

    def test_text_is_kept_when_allowed(self):
        assert as_pk("slug", ClassificationProject, "pk", allow_text=True) == "slug"

    def test_an_object_with_no_pk(self):
        with pytest.raises(TypeError, match="has no pk"):
            as_pk(ClassificationProject.model_construct(), ClassificationProject, "project_pk")


def test_takes_pk_checks_the_names():
    with pytest.raises(TypeError, match="has no parameter nope"):
        @takes_pk(nope=ClassificationProject)
        def method(self, project_pk):  # pragma: no cover
            pass


@pytest.fixture
def client():
    c = MagicMock()
    c.server_version = "v2"
    c.get.return_value = paginated_response([])
    c.get_all.return_value = paginated_response([])
    return c


class TestComponents:

    def test_classification_results_take_a_project(self, client):
        C.ClassificationsComponent(client).get_project_results(_cp(2))
        assert client.get.call_args[0][0].endswith("/results/2/")

    def test_media_takes_a_project_and_a_collection(self, client):
        media = C.ClassificationMediaComponent(client)
        media._resolve_collection_pk = MagicMock(return_value=11)
        media.get_collection_media(_cp(2), Collection.model_construct(pk=5))
        media._resolve_collection_pk.assert_called_once_with(2, 5)

    def test_research_project_collections_take_a_research_project(self, client):
        C.ResearchProjectsComponent(client).get_project_collections(ResearchProject.model_construct(pk=10))
        assert "/10/" in client.get.call_args[0][0]

    def test_a_classification_project_where_a_research_project_goes(self, client):
        with pytest.raises(TypeError, match="ResearchProject, not ClassificationProject"):
            C.ResearchProjectsComponent(client).get_project_collections(_cp(2))
        client.get.assert_not_called()

    def test_the_link_of_a_classification_project(self, client):
        link = ClassificationProjectCollection.model_construct(pk=4)
        C.ClassificationProjectsComponent(client).get_collection_resources(link)
        assert "/4/" in client.get.call_args[0][0]

    def test_resources_by_location(self, client):
        C.ResourcesComponent(client).get_by_location(Location.model_construct(pk=6))
        assert client.get.call_args[0][0].endswith("/location/6")

    def test_find_takes_its_own_schema(self, client):
        client.get_one.return_value = {"pk": 3, "name": "x"}
        C.LocationsComponent(client).find(Location.model_construct(pk=3), validate=False)
        assert client.get_one.call_args[0][0].endswith("/3")

    def test_find_keeps_other_text(self, client):
        client.get_one.return_value = {"pk": 3}
        C.LocationsComponent(client).find("abc", validate=False)
        assert client.get_one.call_args[0][0].endswith("/abc")


def test_every_decorated_parameter_is_annotated_with_its_types():
    """The signatures say what they take: ``int | ClassificationProject``."""
    for name in dir(C):
        cls = getattr(C, name)
        if not isinstance(cls, type):
            continue
        for attr, method in vars(cls).items():
            types = getattr(method, "__pk_types__", None)
            if not types:
                continue
            signature = inspect.signature(method)
            for param, expected in types.items():
                expected = expected if isinstance(expected, tuple) else (expected,)
                annotation = str(signature.parameters[param].annotation)
                assert all(t.__name__ in annotation for t in expected), (cls.__name__, attr, param, annotation)
