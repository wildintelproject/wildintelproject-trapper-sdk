"""
Unit tests for TusUploader and the version-aware client helpers.

A fake tusd (httpx.MockTransport) stands in for the server — no network needed.
"""
from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from trapper_client import err
from trapper_client.api_client_base import APIClientBase
from trapper_client.components.tus_uploader import TusUploader, TusUploaderError, _encode_metadata

BASE = "https://trapper.example.org"


class FakeTusd:
    """Minimal tus 1.0 server: creation + HEAD + PATCH, with a few fault knobs."""

    def __init__(self, reject_create: int | None = None, drop_after_create: bool = False):
        self.uploads: dict[str, dict] = {}
        self.requests: list[tuple[str, str]] = []
        self.reject_create = reject_create
        self.drop_after_create = drop_after_create
        self.fail_patch_once = False

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append((request.method, request.url.path))
        assert request.headers["Tus-Resumable"] == "1.0.0"
        assert request.headers["Authorization"] == "Token tok"
        path = request.url.path
        if request.method == "POST":
            if self.reject_create:
                return httpx.Response(self.reject_create, json={"detail": "HTTP uploader access not granted"})
            uid = f"pkg-{len(self.uploads):032x}"
            meta = dict(p.split(" ", 1) for p in request.headers["Upload-Metadata"].split(","))
            self.uploads[uid] = {"length": int(request.headers["Upload-Length"]), "data": b"",
                                 "meta": {k: base64.b64decode(v).decode() for k, v in meta.items()}}
            # tusd behind a proxy may advertise a wrong host: only the path must be trusted.
            return httpx.Response(201, headers={"Location": f"http://internal:8088/uploader/tus/{uid}"})
        uid = path.rsplit("/", 1)[-1]
        up = self.uploads.get(uid)
        if up is None or (self.drop_after_create and request.method == "HEAD"):
            return httpx.Response(404)
        if request.method == "HEAD":
            return httpx.Response(200, headers={"Upload-Offset": str(len(up["data"])), "Upload-Length": str(up["length"])})
        if request.method == "PATCH":
            if self.fail_patch_once:
                self.fail_patch_once = False
                return httpx.Response(502)
            offset = int(request.headers["Upload-Offset"])
            if offset != len(up["data"]):
                return httpx.Response(409)
            up["data"] += request.content
            return httpx.Response(204, headers={"Upload-Offset": str(len(up["data"]))})
        return httpx.Response(405)


def make_uploader(server: FakeTusd, chunk_size: int = 4, token: str | None = "tok", events=None) -> TusUploader:
    client = APIClientBase(access_token=token, user_name=None if token else "u",
                           user_password=None if token else "p", base_url=BASE, trapper_version="v2")
    cb = (lambda ev, data: events.append((ev, data))) if events is not None else None
    return TusUploader(client=client, chunk_size=chunk_size, progress_callback=cb,
                       transport=httpx.MockTransport(server))


@pytest.fixture
def sample(tmp_path) -> Path:
    f = tmp_path / "package.zip"
    f.write_bytes(b"0123456789")  # 10 bytes -> 3 chunks of 4
    return f


def test_metadata_header_is_base64_pairs():
    header = _encode_metadata({"filename": "a.zip", "path": "x/a.zip"})
    assert header == f"filename {base64.b64encode(b'a.zip').decode()},path {base64.b64encode(b'x/a.zip').decode()}"


def test_upload_sends_whole_file_in_chunks(sample):
    server, events = FakeTusd(), []
    make_uploader(server, events=events).upload(sample, "season1/package.zip")
    up = next(iter(server.uploads.values()))
    assert up["data"] == b"0123456789"
    assert up["meta"] == {"filename": "package.zip", "path": "season1/package.zip"}
    assert [m for m, _ in server.requests].count("PATCH") == 3
    assert [e for e, _ in events] == ["upload_created", "progress", "progress", "progress", "upload_complete"]
    assert events[-2][1] == {"bytes": 10, "total": 10}


def test_location_host_is_replaced_by_base_url(sample):
    server = FakeTusd()
    make_uploader(server).upload(sample, "p.zip")
    patched = {path for method, path in server.requests if method == "PATCH"}
    assert all(p.startswith("/uploader/tus/pkg-") for p in patched)  # right path, on our MockTransport host


def test_sidecar_is_removed_after_success(sample):
    make_uploader(FakeTusd()).upload(sample, "p.zip")
    assert not (sample.parent / "package.zip.tusmeta.json").exists()


def test_interrupted_upload_resumes_from_server_offset(sample):
    server = FakeTusd()
    up = make_uploader(server)
    server.fail_patch_once = False
    # first run: let the first chunk land, then die on the second PATCH for good
    original = server.__call__
    state = {"patches": 0}

    def dying(request):
        if request.method == "PATCH":
            state["patches"] += 1
            if state["patches"] == 2:
                return httpx.Response(400, json={"detail": "boom"})
        return original(request)

    up.transport = httpx.MockTransport(dying)
    with pytest.raises(TusUploaderError, match="Sending a chunk failed: HTTP 400"):
        up.upload(sample, "p.zip")
    assert (sample.parent / "package.zip.tusmeta.json").exists()
    assert len(next(iter(server.uploads.values()))["data"]) == 4

    server.requests.clear()
    make_uploader(server).upload(sample, "p.zip")  # a fresh uploader, as in a new process
    assert len(server.uploads) == 1  # no second upload was created
    assert [m for m, _ in server.requests] == ["HEAD", "PATCH", "PATCH"]  # only the 2 missing chunks
    assert next(iter(server.uploads.values()))["data"] == b"0123456789"


def test_vanished_upload_is_recreated(sample):
    server = FakeTusd()
    first = make_uploader(server)
    url = "https://trapper.example.org/uploader/tus/pkg-gone"
    first._save_state(sample, "p.zip", 10, url)
    make_uploader(server).upload(sample, "p.zip")
    assert len(server.uploads) == 1 and next(iter(server.uploads.values()))["data"] == b"0123456789"


def test_changed_file_does_not_resume(sample):
    uploader = make_uploader(FakeTusd())
    uploader._save_state(sample, "p.zip", 999, "https://trapper.example.org/uploader/tus/x")
    assert uploader._load_state(sample, "p.zip", 10) is None


def test_transient_5xx_is_retried(sample):
    server = FakeTusd()
    server.fail_patch_once = True
    make_uploader(server).upload(sample, "p.zip")
    assert next(iter(server.uploads.values()))["data"] == b"0123456789"


@pytest.mark.parametrize("status", [401, 403, 413])
def test_server_rejection_surfaces_its_detail(sample, status):
    with pytest.raises(TusUploaderError, match=f"HTTP {status}.*not granted"):
        make_uploader(FakeTusd(reject_create=status)).upload(sample, "p.zip")


def test_missing_file_is_reported(tmp_path):
    with pytest.raises(TusUploaderError, match="File not found"):
        make_uploader(FakeTusd()).upload(tmp_path / "nope.zip", "p.zip")


def test_token_is_required():
    uploader = make_uploader(FakeTusd(), token=None)
    with pytest.raises(TusUploaderError, match="access token"):
        uploader._headers()


def test_empty_file_is_uploaded(tmp_path):
    f = tmp_path / "empty.bin"
    f.write_bytes(b"")
    server = FakeTusd()
    make_uploader(server).upload(f, "e.bin")
    assert next(iter(server.uploads.values()))["length"] == 0


# ── upload_auth + get_uploader ────────────────────────────────────────────────

class TestUploadAuth:
    def _client(self, version, status=200, body=None):
        client = APIClientBase(access_token="tok", base_url=BASE, trapper_version=version)
        response = MagicMock(spec=httpx.Response, status_code=status)
        response.headers = {"Content-Type": "application/json"}
        response.json.return_value = body or {"username": "alice"}
        response.text = str(body)
        client._send_request = MagicMock(return_value=response)
        return client

    def test_returns_username_on_v2(self):
        client = self._client("v2")
        assert client.upload_auth() == {"username": "alice"}
        assert client._send_request.call_args[1]["endpoint"] == "storage/api/upload-auth/"

    def test_refused_on_v1(self):
        client = self._client("v1")
        with pytest.raises(err.UnsupportedVersionError, match="only available in Trapper v2"):
            client.upload_auth()
        client._send_request.assert_not_called()

    def test_forbidden_without_uploader_account(self):
        client = self._client("v2", status=403, body={"detail": "HTTP uploader access not granted"})
        with pytest.raises(err.ForbiddenError):
            client.upload_auth()

    def test_unauthorized_with_bad_token(self):
        client = self._client("v2", status=401, body={"detail": "Invalid token"})
        with pytest.raises(err.UnauthorizedError):
            client.upload_auth()


class TestGetUploader:
    def test_v2_gets_the_tus_uploader(self):
        from trapper_client.trapper_client import TrapperClient
        up = TrapperClient(access_token="tok", base_url=BASE, trapper_version="v2").get_uploader(chunk_size=8)
        assert isinstance(up, TusUploader) and up.chunk_size == 8

    def test_v1_gets_the_http_uploader(self):
        pytest.importorskip("blake3")
        pytest.importorskip("aiofiles")
        from trapper_client.components.http_uploader import HTTPUploader
        from trapper_client.trapper_client import TrapperClient
        up = TrapperClient(access_token="tok", base_url=BASE, trapper_version="v1").get_uploader()
        assert isinstance(up, HTTPUploader)
