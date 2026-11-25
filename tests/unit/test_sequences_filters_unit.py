"""
Unit tests for the filters and rows of SequencesComponent (issue #115). Mocked: no server needed.
"""
from __future__ import annotations

import warnings
from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import paginated_response
from trapper_client import err
from trapper_client.components.sequences import SequencesComponent
from trapper_client.schemas import Sequence


@pytest.fixture
def client():
    c = MagicMock()
    c.server_version = "v2"
    c.get.return_value = paginated_response([])
    return c


@pytest.mark.parametrize("given", [[9, 3], (9, 3), "9,3", "9, 3"])
def test_deployment_goes_comma_separated(client, given):
    SequencesComponent(client).get(deployment=given)
    assert client.get.call_args[1]["query"]["deployment"] == "9,3"


def test_search_warns_that_it_answers_500(client):
    with pytest.warns(err.UnknownFilterWarning, match="answers 500"):
        SequencesComponent(client).get(search="x")


def test_unknown_filter_warns(client):
    with pytest.warns(err.UnknownFilterWarning, match="ignores 'name'"):
        SequencesComponent(client).get(name="x")


@pytest.mark.parametrize("name", ["sequence_id", "sequence_uuid", "interval", "collection", "deployment", "pk"])
def test_known_filters_do_not_warn(client, name):
    with warnings.catch_warnings():
        warnings.simplefilter("error", err.UnknownFilterWarning)
        SequencesComponent(client).get(**{name: "1"})


def test_v2_repeated_resources_are_kept_once():
    row = {"pk": 1, "sequence_id": 1, "sequence_uuid": "40085959", "resources": [1, 1, 5, 1],
           "created_at": "2026-11-02T19:10:30Z"}
    assert Sequence.model_validate(row).resources == [1, 5]
