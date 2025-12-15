import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

import aiofiles
import httpx
from blake3 import blake3
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

CHUNK_SIZE = 64 * 1024 * 1024  # 64 MB
READ_CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB

ProgressCallback = Callable[[str, Dict[str, Any]], None]


class HTTPUploaderError(Exception):
    pass

class HTTPUploader:
    """
    Async HTTP uploader with resumable chunk-based uploads.
    UI-agnostic: progress is reported via callbacks.
    """

    def __init__(
        self,
        server_url: str,
        login: str,
        password: str,
        verify: bool = True,
        max_parallel: int = 4,
    ):
        self.server = server_url.rstrip("/")
        self.login = login
        self.password = password
        self.verify = verify
        self.max_parallel = max_parallel

        self.session_id: Optional[str] = None
        self.meta: Dict[str, Any] = {}
        self.meta_path: str = ""
        self._meta_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        cb: ProgressCallback | None,
        event: str,
        **data: Any,
    ) -> None:
        if cb:
            cb(event, data)

    # ------------------------------------------------------------------
    # auth
    # ------------------------------------------------------------------

    async def _login(self) -> str:
        async with httpx.AsyncClient(verify=self.verify) as client:
            response = await client.post(
                f"{self.server}/uploader/auth/login",
                json={"username": self.login, "password": self.password},
            )
            response.raise_for_status()
            data = response.json()
            return data["sessionid"]

    # ------------------------------------------------------------------
    # hashing & metadata
    # ------------------------------------------------------------------

    async def _compute_hashes(
        self,
        path: Path,
        progress_callback: ProgressCallback | None = None,
    ) -> tuple[str, List[str]]:
        size = path.stat().st_size
        total_chunks = (size + CHUNK_SIZE - 1) // CHUNK_SIZE

        self._emit(
            progress_callback,
            "hash_start",
            file=str(path),
            size=size,
            total_chunks=total_chunks,
        )

        full_hasher = blake3()
        chunk_hashes: List[str] = []
        processed = 0

        async with aiofiles.open(path, "rb") as f:
            for idx in range(total_chunks):
                remaining = CHUNK_SIZE
                chunk_hasher = blake3()

                while remaining > 0:
                    buf = await f.read(min(READ_CHUNK_SIZE, remaining))
                    if not buf:
                        break

                    remaining -= len(buf)
                    processed += len(buf)

                    full_hasher.update(buf)
                    chunk_hasher.update(buf)

                    self._emit(
                        progress_callback,
                        "hash_progress",
                        processed=processed,
                        total=size,
                    )

                chunk_hashes.append(chunk_hasher.hexdigest())

        self._emit(
            progress_callback,
            "hash_complete",
            file_hash=full_hasher.hexdigest(),
            chunks=len(chunk_hashes),
        )

        return full_hasher.hexdigest(), chunk_hashes

    async def _update_metadata(self, updater: Callable[[Dict[str, Any]], None]) -> None:
        async with self._meta_lock:
            updater(self.meta)
            tmp = self.meta_path + ".tmp"
            async with aiofiles.open(tmp, "w") as f:
                await f.write(json.dumps(self.meta, indent=2))
            await asyncio.to_thread(os.replace, tmp, self.meta_path)

    async def _create_metadata(
        self,
        file_path: Path,
        remote_path: str,
        file_hash: str,
        chunk_hashes: List[str],
    ) -> None:

        def init(meta: Dict[str, Any]) -> None:
            meta.clear()
            meta.update(
                {
                    "file": str(file_path),
                    "remote": remote_path,
                    "file_hash": file_hash,
                    "chunk_size": CHUNK_SIZE,
                    "total_chunks": len(chunk_hashes),
                    "chunk_hashes": chunk_hashes,
                    "completed": {},
                }
            )

        await self._update_metadata(init)

    def _validate_metadata(self, file_path: Path, remote_path: str, size: int) -> bool:
        return (
            self.meta.get("file") == str(file_path)
            and self.meta.get("remote") == remote_path
            and size
            == sum(
                min(CHUNK_SIZE, size - i * CHUNK_SIZE)
                for i in range(self.meta.get("total_chunks", 0))
            )
        )

    async def _load_or_create_metadata(
        self,
        file_path: Path,
        remote_path: str,
        size: int,
        progress_callback: ProgressCallback | None,
    ) -> tuple[str, List[str]]:
        if os.path.exists(self.meta_path):
            async with self._meta_lock:
                async with aiofiles.open(self.meta_path, "r") as f:
                    self.meta = json.loads(await f.read())

            if self._validate_metadata(file_path, remote_path, size):
                return self.meta["file_hash"], self.meta["chunk_hashes"]

            os.remove(self.meta_path)

        file_hash, chunk_hashes = await self._compute_hashes(
            file_path, progress_callback
        )
        await self._create_metadata(file_path, remote_path, file_hash, chunk_hashes)
        return file_hash, chunk_hashes

    # ------------------------------------------------------------------
    # upload
    # ------------------------------------------------------------------

    async def _init_upload(
        self,
        client: httpx.AsyncClient,
        path: str,
        size: int,
        file_hash: str,
    ) -> Dict[str, Any]:
        response = await client.post(
            f"{self.server}/uploader/upload/init",
            json={"path": path, "size": size, "file_hash": file_hash},
            cookies={"sessionid": self.session_id},
        )
        response.raise_for_status()
        return response.json()

    @retry(
        wait=wait_exponential(min=2, max=15),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(httpx.TransportError),
        reraise=True,
    )
    async def _upload_chunk(
        self,
        client: httpx.AsyncClient,
        file_path: Path,
        remote_path: str,
        index: int,
        offset: int,
        size: int,
        chunk_hash: str,
        progress_callback: ProgressCallback | None,
    ) -> None:

        async def gen():
            async with aiofiles.open(file_path, "rb") as f:
                await f.seek(offset)
                remaining = size
                sent = 0

                while remaining > 0:
                    buf = await f.read(min(READ_CHUNK_SIZE, remaining))
                    if not buf:
                        break

                    remaining -= len(buf)
                    sent += len(buf)
                    yield buf

                    self._emit(
                        progress_callback,
                        "upload_progress",
                        chunk=index,
                        sent=sent,
                        chunk_size=size,
                    )

        response = await client.put(
            f"{self.server}/uploader/upload/chunk/{index}",
            params={
                "path": remote_path,
                "offset": str(offset),
                "size": str(size),
                "hash": chunk_hash,
            },
            cookies={"sessionid": self.session_id},
            content=gen(),
        )
        response.raise_for_status()

    async def _upload_chunks(
        self,
        client: httpx.AsyncClient,
        file_path: Path,
        remote_path: str,
        size: int,
        completed: set[int],
        progress_callback: ProgressCallback | None,
    ) -> None:
        total_chunks = self.meta["total_chunks"]
        sem = asyncio.Semaphore(self.max_parallel)

        async def worker(i: int):
            async with sem:
                if i in completed:
                    return

                offset = i * CHUNK_SIZE
                size_i = min(CHUNK_SIZE, size - offset)

                self._emit(
                    progress_callback,
                    "chunk_start",
                    chunk=i,
                    size=size_i,
                )

                await self._upload_chunk(
                    client,
                    file_path,
                    remote_path,
                    i,
                    offset,
                    size_i,
                    self.meta["chunk_hashes"][i],
                    progress_callback,
                )

                await self._update_metadata(
                    lambda m: m["completed"].update({str(i): True})
                )
                completed.add(i)

                self._emit(progress_callback, "chunk_complete", chunk=i)

        await asyncio.gather(*(worker(i) for i in range(total_chunks)))

    async def _finalize_upload(
        self,
        client: httpx.AsyncClient,
        remote_path: str,
        size: int,
        file_hash: str,
    ) -> None:
        response = await client.post(
            f"{self.server}/uploader/upload/complete",
            json={
                "path": remote_path,
                "size": size,
                "file_hash": file_hash,
                "chunk_hashes": self.meta["chunk_hashes"],
            },
            cookies={"sessionid": self.session_id},
        )
        response.raise_for_status()

        try:
            os.remove(self.meta_path)
        except FileNotFoundError:
            pass

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    async def aupload(
        self,
        file_path: Path,
        remote_path: str,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        if not file_path.exists():
            raise HTTPUploaderError(f"File not found: {file_path}")

        size = file_path.stat().st_size
        self.meta_path = str(file_path) + ".uploadmeta.json"

        self._emit(
            progress_callback,
            "upload_start",
            file=str(file_path),
            remote=remote_path,
            size=size,
        )

        file_hash, _ = await self._load_or_create_metadata(
            file_path, remote_path, size, progress_callback
        )

        completed = set(map(int, self.meta["completed"].keys()))

        async with httpx.AsyncClient(timeout=None, verify=self.verify) as client:
            if not completed:
                await self._init_upload(client, remote_path, size, file_hash)

            await self._upload_chunks(
                client,
                file_path,
                remote_path,
                size,
                completed,
                progress_callback,
            )

            await self._finalize_upload(client, remote_path, size, file_hash)

        self._emit(progress_callback, "upload_complete", file=str(file_path))

    def upload(
        self,
        file_path: Path,
        remote_path: str,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.session_id = asyncio.run(self._login())
        asyncio.run(self.aupload(file_path, remote_path, progress_callback))
