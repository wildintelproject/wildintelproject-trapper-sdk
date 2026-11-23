"""``resources.download()``: save the file of a resource, with the web session and tenacity."""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock

import httpx
import pytest

from trapper_client import err
from trapper_client.components.resources import ResourcesComponent

JPEG = b"\xff\xd8\xff" + b"x" * 100


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("tenacity.nap.time.sleep", lambda s: None)


class FakeResponse:
    def __init__(self, status=200, body=JPEG, headers=None, fail_midway=False):
        self.status_code = status
        self._body = body
        self.fail_midway = fail_midway
        self.headers = {"content-type": "image/jpeg", "content-length": str(len(body))}
        self.headers.update(headers or {})

    def iter_bytes(self):
        yield self._body[:10]
        if self.fail_midway:
            raise httpx.ReadError("connection lost")
        yield self._body[10:]


def make(*answers):
    """A component whose web client answers ``answers`` in turn (a response, or an exception to raise)."""
    client = MagicMock()
    client.base_url = "http://trapper.test/"
    seen = []

    @contextmanager
    def stream(method, url):
        seen.append((method, url))
        answer = answers[min(len(seen) - 1, len(answers) - 1)]
        if isinstance(answer, Exception):
            raise answer
        yield answer

    client._web_client.stream = stream
    return ResourcesComponent(client), client, seen


class TestDownload:

    def test_saves_the_original(self, tmp_path):
        comp, client, seen = make(FakeResponse())
        path = comp.download(29, tmp_path / "a.jpg")
        assert path == tmp_path / "a.jpg" and path.read_bytes() == JPEG
        assert seen == [("GET", "http://trapper.test/storage/resource/media/29/file/")]
        client.session_login.assert_called_once()

    @pytest.mark.parametrize("kind, field", [("original", "file"), ("preview", "pfile"), ("thumbnail", "tfile")])
    def test_kinds(self, tmp_path, kind, field):
        comp, _, seen = make(FakeResponse())
        comp.download(7, tmp_path / "x", kind=kind)
        assert seen[0][1].endswith(f"/storage/resource/media/7/{field}/")

    def test_a_directory_gets_a_name_with_the_extension(self, tmp_path):
        comp, _, _ = make(FakeResponse())
        assert comp.download(29, tmp_path).name == "29-original.jpg"

    def test_the_directory_name_follows_the_kind_and_content_type(self, tmp_path):
        comp, _, _ = make(FakeResponse(headers={"content-type": "video/mp4"}))
        assert comp.download(5, tmp_path, kind="thumbnail").name == "5-thumbnail.mp4"

    def test_missing_folders_are_created(self, tmp_path):
        comp, _, _ = make(FakeResponse())
        assert comp.download(1, tmp_path / "a" / "b" / "x.jpg").exists()

    def test_no_part_file_is_left(self, tmp_path):
        comp, _, _ = make(FakeResponse())
        comp.download(1, tmp_path / "x.jpg")
        assert [p.name for p in tmp_path.iterdir()] == ["x.jpg"]

    def test_unknown_kind_is_refused_before_anything(self, tmp_path):
        comp, client, seen = make(FakeResponse())
        with pytest.raises(ValueError, match="kind"):
            comp.download(1, tmp_path / "x", kind="big")
        assert seen == [] and not client.session_login.called


class TestErrors:

    def test_404_says_it_can_be_the_file_or_the_permission(self, tmp_path):
        comp, _, seen = make(FakeResponse(404, b"<html>"))
        with pytest.raises(err.NotFoundError, match="permission"):
            comp.download(1, tmp_path / "x.jpg")
        assert len(seen) == 1                         # not retried
        assert list(tmp_path.iterdir()) == []

    @pytest.mark.parametrize("status, error", [(401, err.UnauthorizedError), (403, err.ForbiddenError), (500, err.APIError)])
    def test_other_statuses(self, tmp_path, status, error):
        comp, _, seen = make(FakeResponse(status, b""))
        with pytest.raises(error):
            comp.download(1, tmp_path / "x.jpg")
        assert len(seen) == 1

    def test_a_redirect_means_the_session_is_not_valid(self, tmp_path):
        comp, _, _ = make(FakeResponse(302, b"", {"location": "/account/login/"}))
        with pytest.raises(err.UnauthorizedError, match="login"):
            comp.download(1, tmp_path / "x.jpg")

    def test_an_empty_body_with_x_accel_redirect_is_explained(self, tmp_path):
        comp, _, seen = make(FakeResponse(200, b"", {"x-accel-redirect": "/media/protected/a.jpg"}))
        with pytest.raises(err.APIError, match="proxy"):
            comp.download(1, tmp_path / "x.jpg")
        assert len(seen) == 1 and list(tmp_path.iterdir()) == []

    def test_a_genuinely_empty_file_is_saved(self, tmp_path):
        comp, _, _ = make(FakeResponse(200, b""))
        assert comp.download(1, tmp_path / "x.jpg").read_bytes() == b""

    def test_missing_credentials_are_reported(self, tmp_path):
        comp, client, _ = make(FakeResponse())
        client.session_login.side_effect = ValueError("session_login() requires user_name/user_password")
        with pytest.raises(ValueError, match="user_name"):
            comp.download(1, tmp_path / "x.jpg")


class TestRetries:

    def test_a_network_failure_is_retried(self, tmp_path):
        comp, _, seen = make(httpx.ConnectError("down"), FakeResponse())
        assert comp.download(1, tmp_path / "x.jpg").read_bytes() == JPEG
        assert len(seen) == 2

    def test_a_503_is_retried(self, tmp_path):
        comp, _, seen = make(FakeResponse(503, b""), FakeResponse(504, b""), FakeResponse())
        assert comp.download(1, tmp_path / "x.jpg").exists()
        assert len(seen) == 3

    def test_a_download_cut_midway_is_retried_from_the_start(self, tmp_path):
        comp, _, seen = make(FakeResponse(fail_midway=True), FakeResponse())
        assert comp.download(1, tmp_path / "x.jpg").read_bytes() == JPEG
        assert len(seen) == 2 and [p.name for p in tmp_path.iterdir()] == ["x.jpg"]

    def test_it_gives_up_after_the_attempts(self, tmp_path):
        comp, _, seen = make(httpx.ConnectError("down"))
        with pytest.raises(httpx.ConnectError):
            comp.download(1, tmp_path / "x.jpg", retry_attempts=3)
        assert len(seen) == 3 and list(tmp_path.iterdir()) == []

    def test_one_attempt_disables_the_retries(self, tmp_path):
        comp, _, seen = make(FakeResponse(503, b""))
        with pytest.raises(err.TransientDownloadError):
            comp.download(1, tmp_path / "x.jpg", retry_attempts=1)
        assert len(seen) == 1
