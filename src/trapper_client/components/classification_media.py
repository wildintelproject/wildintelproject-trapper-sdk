"""
Component for media exports in classification projects.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from trapper_client.api_query import APIQuery
from trapper_client.components.base import TrapperComponent
from trapper_client.components.classification_projects import ClassificationProjectsComponent
from trapper_client.schemas import MediaRecord, PaginatedResult


class ClassificationMediaComponent(TrapperComponent[MediaRecord]):
    """
    Component for ``/media_classification/api/media`` resource.

    Retrieve, filter, and export classification media data from Trapper.

    **Main endpoints:**

    - ``GET /media_classification/api/media/{project_pk}/``: media for one classification project

    **Available filter fields:**

    | Parameter                | Type                  | Description                                                         |
    |--------------------------|----------------------|---------------------------------------------------------------------|
    | owner                    | boolean              | true = resources where the user is owner or manager                 |
    | deployment               | list of PKs          | Filter by deployment PKs                                            |
    | collection               | list of PKs          | Filter by collection PKs                                            |
    | locations_map            | comma-separated PKs  | Filter by location PKs                                              |
    | rdate_from / rdate_to    | date                 | date_recorded range                                                 |
    | rtime_from / rtime_to    | HH:MM                | Time-of-day range on date_recorded                                  |
    | ftype                    | choice               | Filter by resource type (IMAGE, VIDEO, etc.)                        |
    | classified               | boolean              | Classified by user                                                  |
    | classified_ai            | boolean              | Classified by AI                                                    |
    | approved                 | boolean              | Classification approved                                             |
    | bboxes                   | boolean              | Has bounding boxes                                                  |
    | species                  | list of PKs          | Filter by species PKs                                               |
    | observation_type         | choice               | Filter by observation type                                          |
    | sex                      | choice               | Filter by sex                                                       |
    | age                      | choice               | Filter by age                                                       |

    **Available extra params:**

    | Parameter          | Type   | Default | Description                                      |
    |--------------------|--------|---------|--------------------------------------------------|
    | trapper_url        | bool   | True    | Include absolute Trapper URLs for each media     |
    | trapper_url_token  | bool   | True    | Include access tokens in URLs                    |
    | private_human      | bool   | True    | Include human preview URL                        |
    | private_vehicle    | bool   | True    | Include vehicle preview URL                      |
    | private_species    | list   | []      | List of species to hide                          |

    **Examples:**

        # Get one page of media
        page = client.classification_media.get_project_media(project_pk=7, page_size=200)

        # Iterate over all media in a project
        for row in client.classification_media.where_project_media(project_pk=7, deployment=12):
            print(row)

        # Export all media to CSV
        client.classification_media.export_project_media(project_pk=7, file="/tmp/media.csv")

        # Get media from a specific collection
        page = client.classification_media.get_collection_media(project_pk=7, collection_pk=5)

        # Iterate over media in a collection
        for row in client.classification_media.where_collection_media(project_pk=7, collection_pk=5):
            print(row)

        # Export collection media to CSV
        client.classification_media.export_collection_media(
            project_pk=7, collection_pk=5, file="/tmp/collection_media.csv"
        )

        # Download all media files from a project
        files = client.classification_media.download_project_media_files(
            project_pk=7, output_dir="/tmp/media"
        )

        # Download all media files from a collection (parallel + compressed)
        files = client.classification_media.download_collection_media_files(
            project_pk=7, collection_pk=5, output_dir="/tmp/collection_media",
            parallel=True, compress=True,
        )
    """

    endpoint = "media_classification/api/media/{project_pk}/"
    schema = MediaRecord

    # ── internal helpers ──────────────────────────────────────────────────────

    def _resolve_endpoint(self, project_pk: int) -> str:
        """Build the media endpoint for a given project pk.

        Args:
            project_pk: Classification project primary key.

        Returns:
            Resolved endpoint string.
        """
        return self.endpoint.replace("{project_pk}", str(project_pk))

    def _resolve_collection_pk(self, project_pk: int, collection_pk: int) -> int:
        """Resolve the intermediate collection pk used by the classification project.

        Iterates the project-collection links to find the link pk corresponding
        to the given storage collection pk.

        Args:
            project_pk: Classification project primary key.
            collection_pk: Storage collection primary key.

        Returns:
            The intermediate link pk if found, otherwise the original ``collection_pk``.
        """
        classification_projects = ClassificationProjectsComponent(self.client)
        all_links = classification_projects.get_all_project_collections(project_pk=project_pk)
        for link in all_links.results:
            if link.collection_pk == collection_pk:
                return link.pk
        return collection_pk

    def _extract_media_id(self, media: Any) -> int | None:
        """Extract a media identifier from a dict or Pydantic model.

        Args:
            media: Raw row as ``dict`` or model-like object with ``model_dump``.

        Returns:
            Parsed media ID as ``int`` when present and valid, otherwise ``None``.
        """
        candidates = ("id", "resource_id", "resource", "mediaID", "media_id", "pk")

        if isinstance(media, dict):
            values = media
        elif hasattr(media, "model_dump"):
            values = media.model_dump(mode="python")
        else:
            return None

        for key in candidates:
            value = values.get(key)
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    continue
        return None

    def _extract_file_url(self, media: Any) -> str | None:
        """Extract the ready-to-download file URL from a media row.

        The media list endpoint already returns an absolute ``filePath`` URL
        with the resource's access token embedded in the query string (e.g.
        ``?rt=<token>``) whenever the server-side ``trapper_url``/
        ``trapper_url_token`` flags are enabled (the client's default query).
        Downloading via this URL is required for private resources: the
        underlying Django view that serves media files is a plain view, not
        part of the DRF API, so it ignores the ``Authorization`` header this
        client sends and instead checks that ``rt`` query token.

        Args:
            media: Raw row as ``dict`` or model-like object with ``model_dump``.

        Returns:
            The file URL if present, otherwise ``None``.
        """
        candidates = ("filePath", "url", "fileURL", "file_url")

        if isinstance(media, dict):
            values = media
        elif hasattr(media, "model_dump"):
            values = media.model_dump(mode="python")
        else:
            return None

        for key in candidates:
            value = values.get(key)
            if value:
                return str(value)
        return None

    def _media_rows(self, rows: list[Any]) -> list[tuple[int, str]]:
        """Build ``(media_id, file_url)`` pairs from raw media rows.

        Rows missing either a resolvable id or a download URL are skipped.

        Args:
            rows: Raw rows as returned by the media list endpoint.

        Returns:
            List of ``(media_id, file_url)`` pairs.
        """
        pairs = ((self._extract_media_id(row), self._extract_file_url(row)) for row in rows)
        return [(media_id, file_url) for media_id, file_url in pairs if media_id and file_url]

    def _compress_files(
        self,
        files: list[Path],
        archive_file: str | Path | None = None,
    ) -> Path:
        """Compress a list of files into a ZIP archive.

        Args:
            files: File paths to include in the archive.
            archive_file: Target ZIP path. If ``None``, a temp file is created.

        Returns:
            Path to the created ZIP archive.
        """
        if archive_file is None:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            archive_path = Path(tmp.name)
            tmp.close()
        else:
            archive_path = Path(archive_file)

        archive_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file_path in files:
                if file_path.exists() and file_path.is_file():
                    zf.write(file_path, arcname=file_path.name)
        return archive_path

    def _download_media_files(
        self,
        media_rows: list[tuple[int, str]],
        output_path: Path,
        parallel: bool = False,
        max_workers: int = 4,
        compress: bool = False,
        archive_file: str | Path | None = None,
        retry_attempts: int = 3,
        retry_min_wait: float = 0.5,
        retry_max_wait: float = 8.0,
    ) -> list[Path]:
        """Download a list of media files, with optional parallelism and compression.

        Args:
            media_rows: List of ``(media_id, file_url)`` pairs to download.
                ``file_url`` must be the absolute URL from the row's
                ``filePath`` field (see :meth:`_extract_file_url`).
            output_path: Directory where files will be saved.
            parallel: Whether to use threaded parallel downloads.
            max_workers: Maximum worker threads when ``parallel`` is enabled.
            compress: Whether to create a ZIP archive from downloaded files.
            archive_file: Target ZIP path when ``compress=True``.
            retry_attempts: Maximum number of attempts per file.
            retry_min_wait: Minimum exponential backoff delay in seconds.
            retry_max_wait: Maximum exponential backoff delay in seconds.

        Returns:
            List of paths to successfully downloaded files.
        """
        output_path.mkdir(parents=True, exist_ok=True)

        def _download_one(media_id: int, file_url: str) -> Path:
            return self.download_media_file(
                file_url=file_url,
                file=output_path / f"media_{media_id}",
                retry_attempts=retry_attempts,
                retry_min_wait=retry_min_wait,
                retry_max_wait=retry_max_wait,
            )

        downloaded: list[Path] = []

        if parallel and len(media_rows) > 1:
            workers = max(1, min(max_workers, len(media_rows)))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(_download_one, mid, url) for mid, url in media_rows]
                for future in as_completed(futures):
                    try:
                        downloaded.append(future.result())
                    except Exception:
                        continue
        else:
            for media_id, file_url in media_rows:
                try:
                    downloaded.append(_download_one(media_id, file_url))
                except Exception:
                    continue

        if compress and downloaded:
            self._compress_files(downloaded, archive_file=archive_file)

        return downloaded

    # ── project media ─────────────────────────────────────────────────────────

    def get_project_media(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[MediaRecord]:
        """Fetch one page of media rows for a classification project.

        Args:
            project_pk: Classification project primary key.
            query: Base query parameters.
            page: Page number to fetch.
            page_size: Number of items per page.
            validate: Whether to validate each row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            ``PaginatedResult[MediaRecord]`` for the requested page.
        """
        return self.get(
            query=query,
            page=page,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._resolve_endpoint(project_pk),
            **kwargs,
        )

    def where_project_media(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> APIQuery[MediaRecord]:
        """Return a lazy iterator over media rows for a classification project.

        Args:
            project_pk: Classification project primary key.
            query: Base query parameters.
            page_size: Number of items requested per API page.
            validate: Whether to validate each row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Lazy ``APIQuery[MediaRecord]`` iterator yielding media rows.
        """
        return self.where(
            query=query,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._resolve_endpoint(project_pk),
            **kwargs,
        )

    def export_project_media(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        file: str | Path | None = None,
        validate: bool = True,
        **kwargs: Any,
    ) -> Path | list[BaseModel]:
        """Export all media rows for a classification project to CSV or model list.

        Args:
            project_pk: Classification project primary key.
            query: Base query parameters.
            file: Output CSV file path. If ``None``, returns a list of models.
            validate: Whether to validate rows with Pydantic before writing.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            ``Path`` to the generated CSV when ``file`` is provided,
            otherwise ``list[MediaRecord]``.
        """
        return self.export(
            query=query,
            file=file,
            validate=validate,
            overwrite_endpoint=self._resolve_endpoint(project_pk),
            **kwargs,
        )

    def get_project_media_by_id(
        self,
        project_pk: int,
        media_id: int,
        query: Dict[str, Any] | None = None,
        validate: bool = True,
        **kwargs: Any,
    ) -> MediaRecord | None:
        """Find one media record within a project by its media/resource ID.

        Iterates project media lazily and returns the first matching record.

        Args:
            project_pk: Classification project primary key.
            media_id: Target media/resource identifier.
            query: Base query parameters.
            validate: Whether to validate the matching row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Matching ``MediaRecord`` if found, otherwise ``None``.
        """
        for row in self.where_project_media(
            project_pk=project_pk,
            query=query,
            page_size=200,
            validate=validate,
            **kwargs,
        ):
            if self._extract_media_id(row) == media_id:
                return row
        return None

    def download_project_media_files(
        self,
        project_pk: int,
        output_dir: str | Path | None = None,
        query: Dict[str, Any] | None = None,
        parallel: bool = False,
        max_workers: int = 4,
        compress: bool = False,
        archive_file: str | Path | None = None,
        retry_attempts: int = 3,
        retry_min_wait: float = 0.5,
        retry_max_wait: float = 8.0,
        **kwargs: Any,
    ) -> list[Path]:
        """Download all media files for one classification project.

        Args:
            project_pk: Classification project primary key.
            output_dir: Directory where files are saved. Defaults to current dir.
            query: Base query parameters used to filter media rows.
            parallel: Whether to use threaded parallel downloads.
            max_workers: Maximum worker threads when ``parallel`` is enabled.
            compress: Whether to create a ZIP archive from downloaded files.
            archive_file: Target ZIP path when ``compress=True``.
            retry_attempts: Maximum number of attempts per file download.
            retry_min_wait: Minimum exponential backoff delay in seconds.
            retry_max_wait: Maximum exponential backoff delay in seconds.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            List of paths to successfully downloaded files.
        """
        q = self._merge_query(query, kwargs)
        data = self.client.get_all(self._resolve_endpoint(project_pk), query=q)
        result = self._to_paginated(data, validate=False)
        media_rows = self._media_rows(result.results)

        if archive_file is None and compress:
            archive_file = Path(output_dir or ".") / f"project_{project_pk}_media.zip"

        return self._download_media_files(
            media_rows=media_rows,
            output_path=Path(output_dir or "."),
            parallel=parallel,
            max_workers=max_workers,
            compress=compress,
            archive_file=archive_file,
            retry_attempts=retry_attempts,
            retry_min_wait=retry_min_wait,
            retry_max_wait=retry_max_wait,
        )

    # ── collection media ──────────────────────────────────────────────────────

    def get_collection_media(
        self,
        project_pk: int,
        collection_pk: int,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> PaginatedResult[MediaRecord]:
        """Fetch one page of media rows for a collection within a project.

        Args:
            project_pk: Classification project primary key.
            collection_pk: Storage collection primary key.
            query: Base query parameters.
            page: Page number to fetch.
            page_size: Number of items per page.
            validate: Whether to validate each row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            ``PaginatedResult[MediaRecord]`` for the requested page.
        """
        link_pk = self._resolve_collection_pk(project_pk, collection_pk)
        q = self._merge_query(query, kwargs)
        q["collection"] = link_pk
        return self.get(
            query=q,
            page=page,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._resolve_endpoint(project_pk),
        )

    def where_collection_media(
        self,
        project_pk: int,
        collection_pk: int,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        **kwargs: Any,
    ) -> APIQuery[MediaRecord]:
        """Return a lazy iterator over media rows for a collection within a project.

        Args:
            project_pk: Classification project primary key.
            collection_pk: Storage collection primary key.
            query: Base query parameters.
            page_size: Number of items requested per API page.
            validate: Whether to validate each row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Lazy ``APIQuery[MediaRecord]`` iterator yielding collection media rows.
        """
        link_pk = self._resolve_collection_pk(project_pk, collection_pk)
        q = self._merge_query(query, kwargs)
        q["collection"] = link_pk
        return self.where(
            query=q,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=self._resolve_endpoint(project_pk),
        )

    def export_collection_media(
        self,
        project_pk: int,
        collection_pk: int,
        query: Dict[str, Any] | None = None,
        file: str | Path | None = None,
        validate: bool = True,
        **kwargs: Any,
    ) -> Path | list[BaseModel]:
        """Export all media rows for a collection within a project to CSV or model list.

        Args:
            project_pk: Classification project primary key.
            collection_pk: Storage collection primary key.
            query: Base query parameters.
            file: Output CSV file path. If ``None``, returns a list of models.
            validate: Whether to validate rows with Pydantic before writing.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            ``Path`` to the generated CSV when ``file`` is provided,
            otherwise ``list[MediaRecord]``.
        """
        link_pk = self._resolve_collection_pk(project_pk, collection_pk)
        q = self._merge_query(query, kwargs)
        q["collection"] = link_pk
        return self.export(
            query=q,
            file=file,
            validate=validate,
            overwrite_endpoint=self._resolve_endpoint(project_pk),
        )

    def download_collection_media_files(
        self,
        project_pk: int,
        collection_pk: int,
        output_dir: str | Path | None = None,
        query: Dict[str, Any] | None = None,
        parallel: bool = False,
        max_workers: int = 4,
        compress: bool = False,
        archive_file: str | Path | None = None,
        retry_attempts: int = 3,
        retry_min_wait: float = 0.5,
        retry_max_wait: float = 8.0,
        **kwargs: Any,
    ) -> list[Path]:
        """Download all media files for one collection within a project.

        Args:
            project_pk: Classification project primary key.
            collection_pk: Storage collection primary key.
            output_dir: Directory where files are saved. Defaults to current dir.
            query: Base query parameters used to filter media rows.
            parallel: Whether to use threaded parallel downloads.
            max_workers: Maximum worker threads when ``parallel`` is enabled.
            compress: Whether to create a ZIP archive from downloaded files.
            archive_file: Target ZIP path when ``compress=True``.
            retry_attempts: Maximum number of attempts per file download.
            retry_min_wait: Minimum exponential backoff delay in seconds.
            retry_max_wait: Maximum exponential backoff delay in seconds.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            List of paths to successfully downloaded files.
        """
        link_pk = self._resolve_collection_pk(project_pk, collection_pk)
        q = self._merge_query(query, kwargs)
        q["collection"] = link_pk

        data = self.client.get_all(self._resolve_endpoint(project_pk), query=q)
        result = self._to_paginated(data, validate=False)
        media_rows = self._media_rows(result.results)

        if archive_file is None and compress:
            archive_file = (
                Path(output_dir or ".")
                / f"project_{project_pk}_collection_{collection_pk}_media.zip"
            )

        return self._download_media_files(
            media_rows=media_rows,
            output_path=Path(output_dir or "."),
            parallel=parallel,
            max_workers=max_workers,
            compress=compress,
            archive_file=archive_file,
            retry_attempts=retry_attempts,
            retry_min_wait=retry_min_wait,
            retry_max_wait=retry_max_wait,
        )

    # ── file download ─────────────────────────────────────────────────────────

    def download_media_file(
        self,
        file_url: str,
        file: str | Path | None = None,
        retry_attempts: int = 3,
        retry_min_wait: float = 0.5,
        retry_max_wait: float = 8.0,
    ) -> Path:
        """Download one media file with retry support.

        Args:
            file_url: Absolute download URL for the file, as returned in a
                media row's ``filePath`` field (see :meth:`_extract_file_url`).
                Downloading via this URL — instead of guessing the storage
                endpoint from a media id — is what makes this work for
                private resources too, since it already carries the
                resource's access token in the query string.
            file: Output file path. If ``None``, a temp file is created.
            retry_attempts: Maximum number of download attempts.
            retry_min_wait: Minimum exponential backoff delay in seconds.
            retry_max_wait: Maximum exponential backoff delay in seconds.

        Returns:
            Path to the downloaded media file.
        """
        output_path = self.client._select_file(file)

        @retry(
            reraise=True,
            stop=stop_after_attempt(retry_attempts),
            wait=wait_exponential(multiplier=1, min=retry_min_wait, max=retry_max_wait),
            retry=retry_if_exception_type(Exception),
        )
        def _download_once() -> Path:
            response = self.client.make_request(
                endpoint=file_url, method="GET", raise_on_error=True
            )
            output_path.write_bytes(response.content)
            return output_path

        return _download_once()