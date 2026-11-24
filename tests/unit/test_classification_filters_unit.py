"""Filters of the classification list, the results table and the media table: a warning for what Trapper
ignores, and ``approved`` that works on v1 (where Trapper calls it ``status``)."""
from __future__ import annotations

import warnings
from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import paginated_response
from trapper_client import err
from trapper_client.components.classification_media import ClassificationMediaComponent
from trapper_client.components.classifications import ClassificationsComponent


def make(cls, version="v2"):
    client = MagicMock()
    client.server_version = version
    client.get.return_value = paginated_response([])
    client.get_all.return_value = paginated_response([])
    return cls(client), client


def caught(func, *args, **kwargs):
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        func(*args, **kwargs)
    return [w for w in record if issubclass(w.category, err.UnknownFilterWarning)]


def sent(client):
    return client.get.call_args.kwargs["query"]


LIST = lambda comp, **kw: comp.get(**kw)                                     # noqa: E731
RESULTS = lambda comp, **kw: comp.get_project_results(7, **kw)               # noqa: E731
MEDIA = lambda comp, **kw: comp.get_project_media(7, **kw)                   # noqa: E731
CASES = [
    pytest.param(ClassificationsComponent, LIST, id="list"),
    pytest.param(ClassificationsComponent, RESULTS, id="results"),
    pytest.param(ClassificationMediaComponent, MEDIA, id="media"),
]


@pytest.mark.parametrize("cls, call", CASES)
@pytest.mark.parametrize("name", ["user", "feedback", "confidence", "ai_provider", "bogus"])
@pytest.mark.parametrize("version", ["v1", "v2"])
def test_a_filter_trapper_ignores_is_warned_about(cls, call, name, version):
    """``user``, ``feedback``, ``confidence`` and ``ai_provider`` belong to the user and AI lists."""
    comp, _ = make(cls, version)
    warned = caught(call, comp, **{name: 1})
    assert len(warned) == 1
    assert repr(name) in str(warned[0].message)
    assert "attribute of the project's classificator" in str(warned[0].message)


@pytest.mark.parametrize("cls, call", CASES)
@pytest.mark.parametrize("version", ["v1", "v2"])
def test_the_filters_it_applies_are_not_warned_about(cls, call, version):
    comp, _ = make(cls, version)
    assert not caught(call, comp, project=7, deployment=1, collection=2, species=3, observation_type="animal", sex="male",
                      age="adult", rdate_from="2024-01-01", classified=True, bboxes=True, pk=5)


def test_approved_is_sent_as_status_on_v1():
    """v1 ignores ``approved`` and calls the same filter ``status`` (checked: 24 of 28 either way)."""
    comp, client = make(ClassificationsComponent, "v1")
    assert not caught(LIST, comp, approved=True)
    assert sent(client)["status"] is True
    assert "approved" not in sent(client)


def test_approved_stays_approved_on_v2():
    comp, client = make(ClassificationsComponent, "v2")
    assert not caught(LIST, comp, approved=True)
    assert sent(client)["approved"] is True
    assert "status" not in sent(client)


def test_status_is_only_a_filter_on_v1():
    comp, _ = make(ClassificationsComponent, "v1")
    assert not caught(LIST, comp, status=True)
    comp, _ = make(ClassificationsComponent, "v2")
    assert len(caught(LIST, comp, status=True)) == 1


def test_approved_works_the_same_for_the_results_and_the_media_table():
    for cls, call in ((ClassificationsComponent, RESULTS), (ClassificationMediaComponent, MEDIA)):
        comp, client = make(cls, "v1")
        call(comp, approved=False)
        assert sent(client)["status"] is False


def test_the_version_is_not_asked_for_when_approved_is_not_used():
    comp, client = make(ClassificationsComponent)
    type(client).server_version = property(lambda self: (_ for _ in ()).throw(AssertionError("probed")))
    LIST(comp, deployment=1, project=2)


def test_camtrapdp_is_a_parameter_of_the_results_not_an_unknown_filter():
    comp, _ = make(ClassificationsComponent)
    assert not caught(RESULTS, comp, camtrapdp="False")


def test_the_media_parameters_are_known_and_private_species_is_warned_about():
    comp, _ = make(ClassificationMediaComponent)
    assert not caught(MEDIA, comp, private_human="False", private_vehicle="False", trapper_url_token="True")
    warned = caught(MEDIA, comp, private_species=[1])
    assert len(warned) == 1 and "500" in str(warned[0].message)


class TestDeploymentNeedsProject:
    """Without ``project`` Trapper answers 400 "Select a valid choice" to ``deployment`` and ``collection``."""

    @pytest.mark.parametrize("name", ["deployment", "collection"])
    @pytest.mark.parametrize("method", ["get", "get_all", "where", "all"])
    def test_it_is_refused_before_the_request(self, name, method):
        comp, client = make(ClassificationsComponent)
        with pytest.raises(ValueError, match=f"{name}.*project"):
            getattr(comp, method)(**{name: 19})
        client.get.assert_not_called()
        client.get_all.assert_not_called()

    def test_the_query_dictionary_counts_too(self):
        comp, _ = make(ClassificationsComponent)
        with pytest.raises(ValueError, match="deployment"):
            comp.get(query={"deployment": 19})

    def test_both_are_named(self):
        comp, _ = make(ClassificationsComponent)
        with pytest.raises(ValueError, match="deployment and collection"):
            comp.get(deployment=1, collection=2)

    @pytest.mark.parametrize("method", ["get", "get_all", "where"])
    def test_with_project_it_goes_on(self, method):
        comp, client = make(ClassificationsComponent)
        getattr(comp, method)(project=2, deployment=19, collection=3)
        assert client.get.called or client.get_all.called or method == "where"

    def test_the_project_scoped_methods_do_not_need_it(self):
        """The project is in the URL of the results table."""
        comp, client = make(ClassificationsComponent)
        comp.get_project_results(7, deployment=19, collection=3)
        assert client.get.called

    def test_other_filters_do_not_need_a_project(self):
        comp, client = make(ClassificationsComponent)
        comp.get(species=3, approved=True)
        assert client.get.called
