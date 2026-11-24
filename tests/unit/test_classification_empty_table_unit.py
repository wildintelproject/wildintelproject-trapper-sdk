"""The results and media tables answer ``400 "Empty queryset ..."`` when no row matches: that is an empty result."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from trapper_client import err
from trapper_client.components.classification_media import ClassificationMediaComponent
from trapper_client.components.classifications import ClassificationsComponent

EMPTY = err.BadRequestError('["Empty queryset or you have no permission to access the requested objects."]')
OTHER = err.BadRequestError("{'deployment': ['Select a valid choice. 19 is not one of the available choices.']}")


def make(cls, error):
    client = MagicMock()
    client.server_version = "v2"
    client.get.side_effect = error
    client.get_all.side_effect = error
    client.export_all.side_effect = error
    client._select_file.side_effect = lambda f: __import__("pathlib").Path(f)
    return cls(client), client


READS = [
    pytest.param(ClassificationsComponent, lambda c: c.get_project_results(7), id="results-get"),
    pytest.param(ClassificationsComponent, lambda c: list(c.where_project_results(7)), id="results-where"),
    pytest.param(ClassificationsComponent, lambda c: c.export_project_results(7, file=None), id="results-export"),
    pytest.param(ClassificationMediaComponent, lambda c: c.get_project_media(7), id="media-get"),
    pytest.param(ClassificationMediaComponent, lambda c: list(c.where_project_media(7)), id="media-where"),
    pytest.param(ClassificationMediaComponent, lambda c: c.export_project_media(7, file=None), id="media-export"),
    pytest.param(ClassificationMediaComponent, lambda c: c.get_collection_media(7, 3), id="media-collection"),
]


@pytest.mark.parametrize("cls, read", READS)
def test_an_empty_table_is_an_empty_result(cls, read):
    comp, _ = make(cls, EMPTY)
    comp.get_all  # noqa: B018
    if cls is ClassificationMediaComponent:
        comp._resolve_collection_pk = lambda project_pk, collection_pk: collection_pk
    result = read(comp)
    rows = getattr(result, "results", result)
    assert list(rows) == []


def test_the_pagination_of_an_empty_page_says_zero():
    comp, _ = make(ClassificationMediaComponent, EMPTY)
    page = comp.get_project_media(7)
    assert page.pagination.count == 0


@pytest.mark.parametrize("cls, read", READS)
def test_any_other_error_is_still_an_error(cls, read):
    comp, _ = make(cls, OTHER)
    if cls is ClassificationMediaComponent:
        comp._resolve_collection_pk = lambda project_pk, collection_pk: collection_pk
    with pytest.raises(err.BadRequestError, match="Select a valid choice"):
        read(comp)


def test_a_server_error_is_still_an_error():
    comp, _ = make(ClassificationMediaComponent, err.ServerError("boom"))
    with pytest.raises(err.ServerError):
        comp.get_project_media(7)


def test_the_raw_export_of_an_empty_table_is_an_empty_file(tmp_path):
    comp, _ = make(ClassificationsComponent, EMPTY)
    path = comp.export_project_results(7, file=tmp_path / "out.csv", raw=True)
    assert path.read_text() == ""


@pytest.mark.parametrize("method", ["download_project_media_files"])
def test_downloading_an_empty_table_downloads_nothing(method, tmp_path):
    comp, _ = make(ClassificationMediaComponent, EMPTY)
    assert getattr(comp, method)(7, output_dir=tmp_path) == []


def test_downloading_an_empty_collection_downloads_nothing(tmp_path):
    comp, _ = make(ClassificationMediaComponent, EMPTY)
    comp._resolve_collection_pk = lambda project_pk, collection_pk: collection_pk
    assert comp.download_collection_media_files(7, 3, output_dir=tmp_path) == []
