import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

import aiofiles
import httpx
from blake3 import blake3
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import attr
import logging
import re

from trapper_client.TrapperAPIComponent import TrapperAPIComponent

logger = logging.getLogger(__name__)

CHUNK_SIZE = 64 * 1024 * 1024  # 64 MB
READ_CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB


class HTTPUploaderError(Exception):
    """Base exception for HTTP uploader errors."""
    pass


@attr.s
class HTTPUploader(TrapperAPIComponent):
    """
    HTTPUploader como componente TrapperAPIComponent.

    - Subidas de archivos en chunks
    - Hash BLAKE3 para integridad
    - Resumible con metadata
    - Callback para progreso
    """

    max_parallel: int = attr.ib(default=4)
    progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = attr.ib(default=None)
    session_id: Optional[str] = attr.ib(default=None)
    meta: Dict[str, Any] = attr.ib(factory=dict)
    meta_path: str = attr.ib(default="")
    _meta_lock: asyncio.Lock = attr.ib(factory=asyncio.Lock)

    async def _login(self) -> str:
        """
        Login y obtención de session_id usando TrapperAPIComponent
        """
        r = self._client.post(
            "/uploader/auth/login",
            body={"username": self._client.user_name, "password": self._client.user_password}
        )
        data = r.json()
        if self.progress_callback:
            self.progress_callback("login", {"username": data.get("username")})
        self.session_id = data["sessionid"]
        return self.session_id

    async def _compute_hashes(self, path: str) -> tuple[str, List[str]]:
        """Calcular hash completo y por chunk"""
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

    async def _update_metadata(self, updater: Callable[[Dict[str, Any]], None]) -> None:
        """Actualizar metadata de forma thread-safe y atomica"""
        async with self._meta_lock:
            updater(self.meta)
            tmp = self.meta_path + ".tmp"
            async with aiofiles.open(tmp, "w") as f:
                await f.write(json.dumps(self.meta, indent=2))
            await asyncio.to_thread(os.replace, tmp, self.meta_path)

    async def _create_metadata(
        self, file_path: Path, remote_path: str, file_hash: str, chunk_hashes: List[str]
    ) -> None:
        """Crear metadata inicial"""
        def initialize_meta(meta: Dict[str, Any]) -> None:
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
        await self._update_metadata(initialize_meta)

    def _validate_metadata(self, file_path: Path, remote_path: str, size: int) -> bool:
        """Validar que la metadata existente coincide con el archivo actual"""
        if self.meta.get("file") != str(file_path) or self.meta.get("remote") != remote_path:
            return False
        expected_size = sum(
            min(CHUNK_SIZE, size - i * CHUNK_SIZE)
            for i in range(self.meta.get("total_chunks", 0))
        )
        return size == expected_size

    async def _load_or_create_metadata(
        self, file_path: Path, remote_path: str, size: int
    ) -> tuple[str, List[str]]:
        """Cargar o crear metadata"""
        if os.path.exists(self.meta_path):
            async with self._meta_lock:
                async with aiofiles.open(self.meta_path, "r") as f:
                    self.meta = json.loads(await f.read())
            if not self._validate_metadata(file_path, remote_path, size):
                os.remove(self.meta_path)
                file_hash, chunk_hashes = await self._compute_hashes(str(file_path))
                await self._create_metadata(file_path, remote_path, file_hash, chunk_hashes)
            else:
                file_hash = self.meta["file_hash"]
                chunk_hashes = self.meta["chunk_hashes"]
        else:
            file_hash, chunk_hashes = await self._compute_hashes(str(file_path))
            await self._create_metadata(file_path, remote_path, file_hash, chunk_hashes)
        return file_hash, chunk_hashes

    async def _init_upload(self, client: httpx.AsyncClient, path: str, size: int, file_hash: str) -> Dict[str, Any]:
        """Inicializar sesión de upload en el servidor"""
        response = await client.post(
            f"{self.host}/uploader/upload/init",
            json={"path": path, "size": size, "file_hash": file_hash},
            cookies={"sessionid": self.session_id},
        )
        response.raise_for_status()
        return response.json()

    async def _upload_chunk(
        self, client: httpx.AsyncClient, file_path: str, remote_path: str, index: int,
        offset: int, size: int, chunk_hash: str
    ) -> Dict[str, Any]:
        """Subir un chunk individual"""
        async def body_gen():
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

        url = f"{self.host}/uploader/upload/chunk/{index}"
        response = await client.put(
            url,
            params={"path": remote_path, "offset": offset, "size": size, "hash": chunk_hash},
            cookies={"sessionid": self.session_id},
            content=body_gen()
        )
        response.raise_for_status()
        result = response.json()
        if result.get("status") != "ok":
            raise HTTPUploaderError(f"Server rejected chunk {index}: {result}")
        return result

    async def _upload_chunks(
        self, client: httpx.AsyncClient, file_path: Path, remote_path: str,
        size: int, completed: set[int]
    ) -> None:
        """Subir todos los chunks pendientes en paralelo"""
        total_chunks = self.meta["total_chunks"]
        chunks_to_upload = [i for i in range(total_chunks) if i not in completed]
        sem = asyncio.Semaphore(self.max_parallel)

        async def worker(i: int):
            async with sem:
                if i in completed:
                    return
                offset = i * CHUNK_SIZE
                size_i = min(CHUNK_SIZE, size - offset)
                h = self.meta["chunk_hashes"][i]
                await self._upload_chunk(client, str(file_path), remote_path, i, offset, size_i, h)
                await self._update_metadata(lambda m: m["completed"].update({str(i): h}))
                completed.add(i)

        await asyncio.gather(*(worker(i) for i in chunks_to_upload))

    async def _finalize_upload(
        self, client: httpx.AsyncClient, remote_path: str, size: int, file_hash: str
    ) -> None:
        """Finalizar upload en servidor"""
        chunk_hashes = self.meta["chunk_hashes"]
        response = await client.post(
            f"{self.host}/uploader/upload/complete",
            json={"path": remote_path, "size": size, "file_hash": file_hash, "chunk_hashes": chunk_hashes},
            cookies={"sessionid": self.session_id}
        )
        response.raise_for_status()
        if self.progress_callback:
            self.progress_callback("upload_complete", {"path": remote_path})
        try:
            os.remove(self.meta_path)
        except FileNotFoundError:
            pass

    async def upload_file(self, file_path: Path, remote_path: str) -> None:
        """Subir archivo de manera resumible"""
        if not file_path.exists():
            raise HTTPUploaderError(f"File not found: {file_path}")
        size = os.path.getsize(file_path)
        self.meta_path = str(file_path) + ".uploadmeta.json"

        file_hash, chunk_hashes = await self._load_or_create_metadata(file_path, remote_path, size)
        completed = set(map(int, self.meta["completed"].keys()))

        async with httpx.AsyncClient(timeout=None, verify=True) as client:
            if not completed:
                await self._init_upload(client, remote_path, size, file_hash)
            await self._upload_chunks(client, file_path, remote_path, size, completed)
            await self._finalize_upload(client, remote_path, size, file_hash)

    def upload(self, filepath: Path, remote_path: str) -> None:
        """Wrapper síncrono"""
        self.session_id = asyncio.run(self._login())
        asyncio.run(self.upload_file(filepath, remote_path))
