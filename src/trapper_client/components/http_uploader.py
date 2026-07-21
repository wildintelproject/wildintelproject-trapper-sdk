import asyncio
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import aiofiles
import attr
import httpx
import logging
from blake3 import blake3
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from trapper_client.api_client_base import APIClientBase

logger = logging.getLogger(__name__)

CHUNK_SIZE = 64 * 1024 * 1024   # 64 MB
READ_CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB


class HTTPUploaderError(Exception):
    """Base exception for HTTP uploader errors."""


@attr.s
class HTTPUploader:
    """
    Resumable chunked file uploader for the Trapper upload API.

    - Uploads files in 64 MB chunks using async I/O.
    - BLAKE3 hashes verify both per-chunk and full-file integrity.
    - Progress is persisted in a sidecar ``.uploadmeta.json`` file so an
      interrupted upload can skip already-delivered chunks.
    - An optional ``progress_callback(event, data)`` receives real-time events.

    Usage::

        uploader = HTTPUploader(client=trapper_client)
        uploader.upload(Path("/data/video.mp4"), "storage/project1/video.mp4")
    """

    client: APIClientBase = attr.ib()
    max_parallel: int = attr.ib(default=4)
    progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = attr.ib(default=None)

    _meta: Dict[str, Any] = attr.ib(factory=dict, init=False)
    _meta_path: str = attr.ib(default="", init=False)
    _meta_lock: asyncio.Lock = attr.ib(factory=asyncio.Lock, init=False)

    # ── authentication ────────────────────────────────────────────────────────

    async def _login(self, http: httpx.AsyncClient) -> None:
        """Authenticate and store the session cookie in the shared httpx client."""
        response = await http.post(
            "uploader/auth/login",
            json={"username": self.client.user_name, "password": self.client.user_password},
        )
        response.raise_for_status()
        data = response.json()
        session_id = data["results"][0]["sessionid"]
        http.cookies.set("sessionid", session_id)
        if self.progress_callback:
            self.progress_callback("login", {"username": data.get("username")})

    # ── hashing ───────────────────────────────────────────────────────────────

    async def _compute_hashes(self, path: str) -> tuple[str, List[str]]:
        """Compute full-file and per-chunk BLAKE3 hashes."""
        full_hasher = blake3()
        chunk_hashes = []
        total_size = os.path.getsize(path)
        total_chunks = (total_size + CHUNK_SIZE - 1) // CHUNK_SIZE

        async with aiofiles.open(path, "rb") as f:
            for i in range(total_chunks):
                remaining = CHUNK_SIZE
                chunk_hasher = blake3()
                while remaining > 0:
                    buf = await f.read(min(READ_CHUNK_SIZE, remaining))
                    if not buf:
                        break
                    remaining -= len(buf)
                    full_hasher.update(buf)
                    chunk_hasher.update(buf)
                    if self.progress_callback:
                        self.progress_callback("hash_progress", {"bytes": len(buf)})
                chunk_hashes.append(chunk_hasher.hexdigest())

        return full_hasher.hexdigest(), chunk_hashes

    # ── metadata (resume state) ───────────────────────────────────────────────

    async def _write_metadata(self, updater: Callable[[Dict[str, Any]], None]) -> None:
        """Apply ``updater`` to ``_meta`` and atomically flush to disk."""
        async with self._meta_lock:
            updater(self._meta)
            tmp = self._meta_path + ".tmp"
            async with aiofiles.open(tmp, "w") as f:
                await f.write(json.dumps(self._meta, indent=2))
            os.replace(tmp, self._meta_path)

    async def _create_metadata(
        self, file_path: Path, remote_path: str, file_hash: str, chunk_hashes: List[str]
    ) -> None:
        def _init(meta: Dict[str, Any]) -> None:
            meta.clear()
            meta.update({
                "file": str(file_path),
                "remote": remote_path,
                "file_hash": file_hash,
                "chunk_size": CHUNK_SIZE,
                "total_chunks": len(chunk_hashes),
                "chunk_hashes": chunk_hashes,
                "completed": {},
            })
        await self._write_metadata(_init)

    def _metadata_is_valid(self, file_path: Path, remote_path: str, size: int) -> bool:
        """Return True when the persisted metadata matches the current file and target path."""
        if self._meta.get("file") != str(file_path):
            return False
        if self._meta.get("remote") != remote_path:
            return False
        if self._meta.get("chunk_size") != CHUNK_SIZE:
            return False
        expected_chunks = (size + CHUNK_SIZE - 1) // CHUNK_SIZE
        return self._meta.get("total_chunks") == expected_chunks

    async def _load_or_create_metadata(
        self, file_path: Path, remote_path: str, size: int
    ) -> tuple[str, List[str]]:
        if os.path.exists(self._meta_path):
            async with self._meta_lock:
                async with aiofiles.open(self._meta_path, "r") as f:
                    self._meta = json.loads(await f.read())
            if self._metadata_is_valid(file_path, remote_path, size):
                return self._meta["file_hash"], self._meta["chunk_hashes"]
            os.remove(self._meta_path)

        file_hash, chunk_hashes = await self._compute_hashes(str(file_path))
        await self._create_metadata(file_path, remote_path, file_hash, chunk_hashes)
        return file_hash, chunk_hashes

    # ── server communication ──────────────────────────────────────────────────

    async def _init_upload(
        self, http: httpx.AsyncClient, path: str, size: int, file_hash: str
    ) -> Dict[str, Any]:
        response = await http.post(
            "uploader/upload/init",
            json={"path": path, "size": size, "file_hash": file_hash},
        )
        response.raise_for_status()
        return response.json()

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=0.5, max=8),
    )
    async def _upload_chunk(
        self,
        http: httpx.AsyncClient,
        file_path: str,
        remote_path: str,
        index: int,
        offset: int,
        size: int,
        chunk_hash: str,
    ) -> Dict[str, Any]:
        async def _body():
            async with aiofiles.open(file_path, "rb") as f:
                await f.seek(offset)
                remaining = size
                while remaining > 0:
                    buf = await f.read(min(READ_CHUNK_SIZE, remaining))
                    if not buf:
                        break
                    remaining -= len(buf)
                    yield buf
                    if self.progress_callback:
                        self.progress_callback("chunk_progress", {"chunk": index, "bytes": len(buf)})

        response = await http.put(
            f"uploader/upload/chunk/{index}",
            params={"path": remote_path, "offset": offset, "size": size, "hash": chunk_hash},
            content=_body(),
        )
        response.raise_for_status()
        result = response.json()
        if result.get("status") != "ok":
            raise HTTPUploaderError(f"Server rejected chunk {index}: {result}")
        return result

    async def _upload_chunks(
        self,
        http: httpx.AsyncClient,
        file_path: Path,
        remote_path: str,
        size: int,
        completed: set[int],
    ) -> None:
        total_chunks = self._meta["total_chunks"]
        pending = [i for i in range(total_chunks) if i not in completed]
        sem = asyncio.Semaphore(self.max_parallel)

        async def _worker(i: int) -> None:
            async with sem:
                offset = i * CHUNK_SIZE
                chunk_size = min(CHUNK_SIZE, size - offset)
                chunk_hash = self._meta["chunk_hashes"][i]
                await self._upload_chunk(http, str(file_path), remote_path, i, offset, chunk_size, chunk_hash)
                await self._write_metadata(lambda m: m["completed"].update({str(i): chunk_hash}))

        await asyncio.gather(*(_worker(i) for i in pending))

    async def _finalize_upload(
        self, http: httpx.AsyncClient, remote_path: str, size: int, file_hash: str
    ) -> None:
        response = await http.post(
            "uploader/upload/complete",
            json={
                "path": remote_path,
                "size": size,
                "file_hash": file_hash,
                "chunk_hashes": self._meta["chunk_hashes"],
            },
        )
        response.raise_for_status()
        if self.progress_callback:
            self.progress_callback("upload_complete", {"path": remote_path})
        try:
            os.remove(self._meta_path)
        except FileNotFoundError:
            pass

    # ── public API ────────────────────────────────────────────────────────────

    async def upload_file(self, file_path: Path, remote_path: str) -> None:
        """Upload ``file_path`` to ``remote_path`` resuming from prior progress if available.

        Note: each call opens a fresh server session via login + init. If the
        previous session was interrupted *after* init but chunks are still
        present on the server, ``_init_upload`` is skipped and those chunks are
        reused. If the server session expired between calls, missing chunks will
        fail on the server and must be re-uploaded.
        """
        if not file_path.exists():
            raise HTTPUploaderError(f"File not found: {file_path}")

        size = os.path.getsize(file_path)
        self._meta_path = str(file_path) + ".uploadmeta.json"

        base_url = self.client.base_url.rstrip("/") + "/"
        async with httpx.AsyncClient(
            base_url=base_url,
            timeout=None,
            verify=self.client.verify_ssl,
        ) as http:
            await self._login(http)
            file_hash, _ = await self._load_or_create_metadata(file_path, remote_path, size)
            completed = set(map(int, self._meta["completed"].keys()))

            if not completed:
                await self._init_upload(http, remote_path, size, file_hash)

            await self._upload_chunks(http, file_path, remote_path, size, completed)
            await self._finalize_upload(http, remote_path, size, file_hash)

    def upload(self, file_path: Path, remote_path: str) -> None:
        """Synchronous wrapper around :meth:`upload_file`."""
        asyncio.run(self.upload_file(file_path, remote_path))
