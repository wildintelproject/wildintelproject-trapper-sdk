"""Batch downloads of the media table: what failed is reported, a run can be repeated, no Pydantic warnings."""
from __future__ import annotations

import warnings
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from trapper_client import err
from trapper_client.components.classification_media import ClassificationMediaComponent, DownloadedFiles

ROWS = [(1, "http://t/1?rt=a"), (2, "http://t/2"), (3, "http://t/3?rt=c")]


def comp_with(failing=(2,)):
    comp = ClassificationMediaComponent(MagicMock())

    def fake(file_url, file=None, **kw):
        media = int(file_url.split("/")[-1].split("?")[0])
        if media in failing:
            raise err.NotFoundError("404")
        Path(file).write_bytes(b"x")
        return Path(file)

    comp.download_media_file = MagicMock(side_effect=fake)
    return comp


@pytest.mark.parametrize("parallel", [False, True])
def test_a_failure_is_reported_and_the_rest_downloaded(tmp_path, parallel):
    result = comp_with()._download_media_files(ROWS, tmp_path, parallel=parallel)
    assert isinstance(result, DownloadedFiles) and isinstance(result, list)
    assert sorted(p.name for p in result) == ["media_1", "media_3"]
    assert list(result.failed) == [2] and "404" in result.failed[2]
    assert not result.ok


def test_nothing_failed_is_ok(tmp_path):
    result = comp_with(failing=())._download_media_files(ROWS, tmp_path)
    assert result.ok and result.failed == {} and len(result) == 3


@pytest.mark.parametrize("parallel", [False, True])
def test_on_error_raise_stops(tmp_path, parallel):
    with pytest.raises(err.NotFoundError):
        comp_with()._download_media_files(ROWS, tmp_path, parallel=parallel, on_error="raise")


def test_a_wrong_on_error_is_refused(tmp_path):
    with pytest.raises(ValueError, match="on_error"):
        comp_with()._download_media_files(ROWS, tmp_path, on_error="ignore")


def test_skip_existing_leaves_the_files_that_are_there(tmp_path):
    (tmp_path / "media_1").write_bytes(b"old")
    comp = comp_with(failing=())
    result = comp._download_media_files(ROWS, tmp_path, skip_existing=True)
    assert [p.name for p in result.skipped] == ["media_1"]
    assert sorted(p.name for p in result) == ["media_2", "media_3"]
    assert (tmp_path / "media_1").read_bytes() == b"old"
    assert comp.download_media_file.call_count == 2


def test_by_default_existing_files_are_downloaded_again(tmp_path):
    (tmp_path / "media_1").write_bytes(b"old")
    result = comp_with(failing=())._download_media_files(ROWS, tmp_path)
    assert len(result) == 3 and result.skipped == []


def test_the_failures_are_logged(tmp_path, caplog):
    with caplog.at_level("WARNING"):
        comp_with()._download_media_files(ROWS, tmp_path)
    assert "1 of 3 media files were not downloaded" in caplog.text


def test_the_public_methods_pass_on_error_and_skip_existing(tmp_path):
    client = MagicMock()
    client.get_all.return_value = {"pagination": {"page": 1, "pages": 1}, "results": []}
    comp = ClassificationMediaComponent(client)
    comp._download_media_files = MagicMock(return_value=DownloadedFiles())
    comp.download_project_media_files(7, output_dir=tmp_path, on_error="raise", skip_existing=True)
    assert comp._download_media_files.call_args.kwargs["on_error"] == "raise"
    assert comp._download_media_files.call_args.kwargs["skip_existing"] is True


def test_reading_the_rows_of_a_download_gives_no_pydantic_warnings():
    """The rows are built without validation, as text; dumping them used to warn twice for each."""
    from trapper_client.schemas import Media

    row = Media.model_construct(mediaID="10", filePublic="true", favorite="false", filePath="http://t/10?rt=a",
                                timestamp="2024-03-12T23:24:35+0100")
    comp = ClassificationMediaComponent(MagicMock())
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert comp._media_rows([row]) == [(10, "http://t/10?rt=a")]
