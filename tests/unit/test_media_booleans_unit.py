"""``private_human`` and the other booleans of the media table go as the text ``True``/``False``."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import paginated_response
from trapper_client.components.classification_media import ClassificationMediaComponent

NAMES = ["private_human", "private_vehicle", "trapper_url", "trapper_url_token"]


def make():
    client = MagicMock()
    client.server_version = "v2"
    client.get.return_value = paginated_response([])
    client.get_all.return_value = paginated_response([])
    return ClassificationMediaComponent(client), client


def sent(client):
    return client.get.call_args.kwargs["query"]


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("value, expected", [
    (True, "True"), (False, "False"),
    ("true", "True"), ("True", "True"), ("TRUE", "True"), (" true ", "True"),
    ("false", "False"), ("False", "False"), ("FALSE", "False"),
])
def test_the_value_goes_as_the_text_trapper_reads(name, value, expected):
    """Trapper compares with ``"True"``: a Python ``True`` (sent as ``true``) used to be read as false."""
    comp, client = make()
    comp.get_project_media(7, **{name: value})
    assert sent(client)[name] == expected


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("value", [1, 0, "yes", "", None, [True]])
def test_anything_else_is_refused_before_the_request(name, value):
    comp, client = make()
    with pytest.raises(ValueError, match=name):
        comp.get_project_media(7, **{name: value})
    client.get.assert_not_called()


@pytest.mark.parametrize("method", ["get_project_media", "where_project_media", "export_project_media"])
def test_every_way_of_reading_the_table_converts(method):
    comp, client = make()
    if method == "where_project_media":
        q = comp.where_project_media(7, private_human=True).query
    else:
        client.get_all.return_value = paginated_response([])
        getattr(comp, method)(7, private_human=True) if method != "export_project_media" else comp.export_project_media(7, file=None, private_human=True)
        mock = client.get if method == "get_project_media" else (client.get_all if client.get_all.called else client.get)
        q = mock.call_args.kwargs["query"]
    assert q["private_human"] == "True"


def test_the_other_filters_are_left_alone():
    comp, client = make()
    comp.get_project_media(7, bboxes=True, sex="male", private_human=False)
    assert sent(client)["bboxes"] is True
    assert sent(client)["sex"] == "male"
    assert sent(client)["private_human"] == "False"


def test_the_collection_methods_and_the_downloads_convert_too():
    comp, client = make()
    comp.get_collection_media(7, 3, private_vehicle=True)
    assert sent(client)["private_vehicle"] == "True"
