"""
Resumable file uploader for Trapper v2 (tus 1.0 protocol, served by tusd).

Trapper v2 replaced the v1 chunked uploader (``uploader/upload/*``) with
`tusd <https://github.com/tus/tusd>`_. Every authorization decision stays in Django
(a ``pre-create`` hook); tusd only moves bytes and the protocol is resumable by design.

Only the standard tus ``creation`` extension is used, plus ``Upload-Metadata``:

* ``filename`` — base name of the file.
* ``path`` — target path relative to the user's directory (package upload).

The tus server lives at ``{base_url}/uploader/tus/`` and authenticates the user from the
``Authorization: Token <key>`` header, so the client needs an ``access_token``.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib.parse import urljoin, urlparse

import attr
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from trapper_client.api_client_base import APIClientBase

logger = logging.getLogger(__name__)

TUS_VERSION = "1.0.0"
TUS_ENDPOINT = "uploader/tus/"
CHUNK_SIZE = 16 * 1024 * 1024  # 16 MB per PATCH


class TusUploaderError(Exception):
    """Base exception for tus uploader errors."""


class _RetryableHTTPError(Exception):
    """A response worth retrying (5xx)."""


def _encode_metadata(metadata: Dict[str, str]) -> str:
    """Build the ``Upload-Metadata`` header: ``key base64(value)`` pairs, comma separated."""
    return ",".join(
        f"{key} {base64.b64encode(value.encode()).decode()}" for key, value in metadata.items()
    )


@attr.s
class TusUploader:
    """
    Resumable uploader for Trapper v2 (tus 1.0).

    - Uploads in ``chunk_size`` PATCH requests; an interrupted upload continues from the
      last byte the server holds (asked with ``HEAD``).
    - The upload URL is persisted in a sidecar ``<file>.tusmeta.json`` so a later run, even
      from another process, resumes instead of starting over.
    - An optional ``progress_callback(event, data)`` receives ``upload_created``,
      ``upload_resumed``, ``progress`` and ``upload_complete`` events.

    Usage::

        uploader = TusUploader(client=trapper_client)
        uploader.upload(Path("/data/package.zip"), "season1/package.zip")
    """

    client: APIClientBase = attr.ib()
    chunk_size: int = attr.ib(default=CHUNK_SIZE)
    progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = attr.ib(default=None)
    #: Custom httpx transport (used by the tests to stand in for tusd).
    transport: Optional[httpx.AsyncBaseTransport] = attr.ib(default=None, repr=False)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _headers(self) -> Dict[str, str]:
        if not self.client.access_token:
            raise TusUploaderError(
                "Trapper v2 uploads authenticate with an access token (Authorization: Token ...); "
                "create the client with access_token=..."
            )
        return {"Tus-Resumable": TUS_VERSION, "Authorization": f"Token {self.client.access_token}"}

    def _emit(self, event: str, **data: Any) -> None:
        if self.progress_callback:
            self.progress_callback(event, data)

    def _resolve_location(self, location: str) -> str:
        """Turn the ``Location`` tusd answered into a URL on the server we talk to.

        Behind a reverse proxy tusd may build the URL from the wrong host/scheme; only the
        path is trusted, and it is re-attached to ``base_url``.
        """
        base = self.client.base_url.rstrip("/") + "/"
        parsed = urlparse(urljoin(base + TUS_ENDPOINT, location))
        return urljoin(base, parsed.path.lstrip("/"))

    @staticmethod
    def _meta_path(file_path: Path) -> Path:
        return file_path.with_name(file_path.name + ".tusmeta.json")

    def _load_state(self, file_path: Path, remote_path: str, size: int) -> Optional[str]:
        """Return the stored upload URL when it still describes this very upload."""
        try:
            meta = json.loads(self._meta_path(file_path).read_text())
        except (OSError, ValueError):
            return None
        mtime = int(file_path.stat().st_mtime)
        if (meta.get("remote") == remote_path and meta.get("size") == size
                and meta.get("mtime") == mtime and meta.get("server") == self.client.base_url):
            return meta.get("url")
        return None

    def _save_state(self, file_path: Path, remote_path: str, size: int, url: str) -> None:
        self._meta_path(file_path).write_text(json.dumps({
            "url": url, "remote": remote_path, "size": size,
            "mtime": int(file_path.stat().st_mtime), "server": self.client.base_url,
        }))

    def _clear_state(self, file_path: Path) -> None:
        try:
            self._meta_path(file_path).unlink()
        except FileNotFoundError:
            pass

    @staticmethod
    def _error(response: httpx.Response, action: str) -> TusUploaderError:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        return TusUploaderError(f"{action} failed: HTTP {response.status_code} - {str(detail)[:300]}")

    # ── protocol ──────────────────────────────────────────────────────────────

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, _RetryableHTTPError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=0.5, max=8),
        reraise=True,
    )
    async def _request(self, http: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> httpx.Response:
        response = await http.request(method, url, **kwargs)
        if response.status_code >= 500:
            raise _RetryableHTTPError(f"{method} {url} -> {response.status_code}")
        return response

    async def _create(self, http: httpx.AsyncClient, file_path: Path, remote_path: str, size: int) -> str:
        """``POST`` the creation request; return the new upload's URL."""
        response = await self._request(
            http, "POST", self.client.base_url.rstrip("/") + "/" + TUS_ENDPOINT,
            headers={
                "Upload-Length": str(size),
                "Upload-Metadata": _encode_metadata({"filename": file_path.name, "path": remote_path}),
            },
        )
        if response.status_code != 201:
            raise self._error(response, "Creating the upload")
        location = response.headers.get("Location")
        if not location:
            raise TusUploaderError("The server accepted the upload but sent no Location header")
        return self._resolve_location(location)

    async def _offset(self, http: httpx.AsyncClient, url: str) -> Optional[int]:
        """``HEAD`` the upload; return the bytes the server holds, or ``None`` if it is gone."""
        response = await self._request(http, "HEAD", url)
        if response.status_code in (404, 410, 403):
            return None
        if response.status_code != 200:
            raise self._error(response, "Reading the upload offset")
        return int(response.headers["Upload-Offset"])

    async def _send(self, http: httpx.AsyncClient, file_path: Path, url: str, size: int, offset: int) -> None:
        """``PATCH`` the file from ``offset`` to the end, ``chunk_size`` bytes at a time."""
        with open(file_path, "rb") as f:
            while offset < size:
                f.seek(offset)
                chunk = await asyncio.to_thread(f.read, min(self.chunk_size, size - offset))
                if not chunk:
                    raise TusUploaderError(f"{file_path} is shorter than the {size} bytes announced")
                response = await self._request(
                    http, "PATCH", url, content=chunk,
                    headers={"Upload-Offset": str(offset), "Content-Type": "application/offset+octet-stream"},
                )
                if response.status_code == 409:  # offset mismatch: ask where the server really is
                    server_offset = await self._offset(http, url)
                    if server_offset is None:
                        raise TusUploaderError("The upload disappeared from the server mid-transfer")
                    offset = server_offset
                    continue
                if response.status_code != 204:
                    raise self._error(response, "Sending a chunk")
                offset = int(response.headers["Upload-Offset"])
                self._emit("progress", bytes=offset, total=size)

    # ── public API ────────────────────────────────────────────────────────────

    async def upload_file(self, file_path: Path, remote_path: str) -> None:
        """Upload ``file_path`` to ``remote_path`` (relative to the user's directory), resuming if possible."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise TusUploaderError(f"File not found: {file_path}")
        size = os.path.getsize(file_path)

        async with httpx.AsyncClient(
            headers=self._headers(), timeout=httpx.Timeout(300.0, connect=30.0),
            verify=self.client.verify_ssl, transport=self.transport,
        ) as http:
            url = self._load_state(file_path, remote_path, size)
            offset = await self._offset(http, url) if url else None
            if offset is None:
                url = await self._create(http, file_path, remote_path, size)
                self._save_state(file_path, remote_path, size, url)
                offset = 0
                self._emit("upload_created", url=url)
            else:
                self._emit("upload_resumed", url=url, offset=offset)

            await self._send(http, file_path, url, size, offset)

        self._clear_state(file_path)
        self._emit("upload_complete", path=remote_path)

    def upload(self, file_path: Path, remote_path: str) -> None:
        """Synchronous wrapper around :meth:`upload_file`."""
        asyncio.run(self.upload_file(file_path, remote_path))
