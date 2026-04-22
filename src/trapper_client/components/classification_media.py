"""
Component for media exports in classification projects.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
import zipfile
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Dict, List

from attr.setters import validate
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from trapper_client.components.classification_project_collections import ClassificationProjectsCollectionsComponent
#from trapper_api_client.components.collections import CollectionsComponent
from trapper_client.components.research_projects import ResearchProjectsComponent
from trapper_client.components.classification_projects import ClassificationProjectsComponent
from trapper_client.api_query import APIQuery
from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import MediaRecord, PaginatedResult, ClassificationProject, ResearchProject, \
    ResearchProjectCollection


class ClassificationMediaComponent(TrapperComponent[MediaRecord]):
    """
    Component for ``/media_classification/api/media`` resource.

    Retrieve, filter, and export classification media data from Trapper.

    **Main endpoints:**
    - ``GET /media_classification/api/media/{project_pk}``: media export for one classification project

    **Available filter fields:**

    | Parameter                | Type                  | Description                                                         |
    |--------------------------|----------------------|---------------------------------------------------------------------|
    | project                  | PK                   | Auto — filtrado por URL (project_pk), no necesita pasarlo           |
    | owner                    | boolean              | true = resources donde el usuario es owner o manager                |
    | deployment               | list of PKs          | Filter by deployment PKs                                            |
    | collection               | list of PKs          | Filter by collection PKs                                            |
    | locations_map            | comma-separated PKs  | Filter by location PKs                                              |
    | rdate_from / rdate_to    | date                 | date_recorded range                                                 |
    | rtime_from / rtime_to    | HH:MM                | Time-of-day range on date_recorded                                  |
    | ftype                    | choice               | Filter by resource type (IMAGE, VIDEO, etc.)                        |
    | classified               | boolean              | Clasificado por usuario                                             |
    | classified_ai            | boolean              | Clasificado por IA                                                  |
    | approved                 | boolean              | Clasificación aprobada                                              |
    | bboxes                   | boolean              | Tiene bboxes                                                        |
    | species                  | list of PKs          | Filter by species PKs                                               |
    | observation_type         | choice               | Filter by observation type                                          |
    | sex                      | choice               | Filter by sex                                                       |
    | age                      | choice               | Filter by age                                                       |

    ** Available extra param: **

    |--------------------|-------------|----------|-------------|
    | Parameter          | Type        | Default  | Description |
    |--------------------|-------------|----------|-------------|
    | trapper_url        | Bool        | True     | Incluye URLs absolutas a TrapPer para cada media
    | trapper_url_token  | Bool        | True     |	Incluye tokens de acceso en las URLs
    | private_human      | Bool        | True	  | Incluye URL de preview de humanos
    | private_vehicle    | Bool        | True     |	Incluye URL de preview de vehículos
    | private_species    | List	       | []	      | Lista de especies a ocultar

    ** Example:: **

        # Get one page of media
        page = client.classification_media.get_project_media(project_pk=7, page_size=200)
        print(page.pagination, len(page.results))

        # Iterate over all media in a project
        for row in client.classification_media.where_project_media(project_pk=7, deployment=12):
            print(row)

        # Export all media to CSV
        client.classification_media.export_project_media(project_pk=7, file="/tmp/media.csv")

        # Get a specific media record by ID
        media = client.classification_media.get_project_media_by_id(project_pk=7, media_id=123)

        # Get media from a specific collection
        page = client.classification_media.get_collection_media(project_pk=7, collection_pk=5)

        # Iterate over media in a collection
        for row in client.classification_media.where_collection_media(project_pk=7, collection_pk=5):
            print(row)

        # Export collection media to CSV
        client.classification_media.export_collection_media(project_pk=7, collection_pk=5, file="/tmp/collection_media.csv")

        # Download individual media files
        path = client.classification_media.download_media_file(media_id=42)

        # Download all media files from a project
        files = client.classification_media.download_project_media_files(project_pk=7, output_dir="/tmp/media")

        # Download all media files from a collection
        files = client.classification_media.download_collection_media_files(
            project_pk=7, collection_pk=5, output_dir="/tmp/collection_media"
        )
    """

    endpoint = "media_classification/api/media/{project_pk}"
    schema = MediaRecord

    def get_project_media(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs,
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
            Paginated result containing ``MediaRecord`` items for the requested page.
        """
        q = self._merge_query(query, kwargs)
        q = dict(q or {})
        q["project_pk"] = project_pk
        q.setdefault("page", page)
        q.setdefault("page_size", page_size)

        endpoint = self.endpoint.replace("{project_pk}", str(project_pk))
        q.pop("project_pk", None)
        data = self.client.get(endpoint, query=q)
        return self._to_paginated(data, validate=validate)

    def where_project_media(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate : bool = True,
        **kwargs,
    ) -> APIQuery:
        """Return a lazy iterator over media rows for a classification project.

        Args:
            project_pk: Classification project primary key.
            query: Base query parameters.
            page_size: Number of items requested per API page.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Lazy ``APIQuery`` iterator yielding project media rows.
        """
        q = self._merge_query(query, kwargs)
        q = dict(q or {})
        q["project_pk"] = project_pk
        endpoint = self.endpoint.replace("{project_pk}", str(project_pk))
        q.pop("project_pk", None)

        """return       self,
        client,
        endpoint: str,
        query: dict[str, Any] | None = None,
        schema: type[TModel] | None = None,
        filter_fn: Callable[[TModel | dict], bool] | None = None,
        page_size: int = 50,
        validate: bool = True
        """
        return APIQuery(client=self.client, endpoint=endpoint, query=q, page_size=page_size, schema=self.schema, validate=validate)


    def export_project_media(
        self,
        project_pk: int,
        query: Dict[str, Any] | None = None,
        file: str | Path | None = None,
        validate: bool = True,
        **kwargs,
    ) -> Path:
        """Export media rows of one classification project to CSV.

        Args:
            project_pk: Classification project primary key.
            query: Base query parameters.
            file: Output CSV file path. If ``None``, a temp file is created.
            validate: If ``True``, validates rows before writing CSV.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Path to the generated CSV file.
        """
        q = self._merge_query(query, kwargs)
        q = dict(q or {})
        q["project_pk"] = project_pk

        endpoint = self.endpoint.replace("{project_pk}", str(project_pk))
        q.pop("project_pk", None)

        if not validate:
            return self.client.export_all(endpoint, query=q, file=file)

        data = self.client.get_all(endpoint, query=q)
        parsed = self._to_paginated(data, validate=True)
        output_path = self.client._select_file(file)
        rows = [item.model_dump(mode="json") for item in parsed.results]
        self.client._write_csv(rows, output_path)
        return output_path

    """ es un find pq devuelve solo uno"""
    def get_project_media_by_id(
        self,
        project_pk: int,
        media_id: int,
        query: Dict[str, Any] | None = None,
        validate: bool = True,
        **kwargs,
    ) -> MediaRecord | None:
        """Get one media record from a classification project by media/resource ID.

        Tries common server-side filter names first and, if needed, falls back
        to local matching over project media pages.

        Args:
            project_pk: Classification project primary key.
            media_id: Target media/resource identifier.
            query: Base query parameters.
            validate: Whether to validate each candidate row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Matching ``MediaRecord`` if found, otherwise ``None``.
        """
        q = self._merge_query(query, kwargs)
        q = dict(q or {})

        # Try likely server-side filters first, then fallback to local matching.
        for key in ("id", "resource", "resource_id", "mediaID", "media_id"):
            qq = dict(q)
            qq[key] = media_id
            endpoint = self.endpoint.replace("{project_pk}", str(project_pk))
            data = self.client.get(endpoint, query=qq)
            result = self._to_paginated(data, validate=validate)
            if result.results:
                return result.results[0]

        for row in self.where_project_media(project_pk=project_pk, query=q, page_size=200):
            row_id = self._extract_media_id(row)
            if row_id == media_id:
                return self._to_model(row, validate=validate)
        return None

    def _extract_media_id(self, media: Any) -> int | None:
        """Extract a media identifier from dict or Pydantic-like records.

        Args:
            media: Raw row as ``dict`` or model-like object with ``model_dump``.

        Returns:
            Parsed media ID as ``int`` when present and valid, otherwise ``None``.
        """
        candidates = ("id", "resource_id", "resource", "mediaID", "media_id", "pk")

        values: Dict[str, Any]
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

    def _compress_files(self, files: list[Path], archive_file: str | Path | None = None) -> Path:
        """Compress downloaded files into a ZIP archive.

        Args:
            files: File paths to include in the archive.
            archive_file: Target ZIP path. If ``None``, a temp ZIP is created.

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

    def get_collection_media(
        self,
        project_pk: int,
        collection_pk: int,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        **kwargs,
    ) -> PaginatedResult[MediaRecord]:
        """Get one page of media rows for a collection within a project.

        Args:
            project_pk: Classification project primary key.
            collection_pk: Collection primary key used for filtering.
            query: Base query parameters.
            page: Page number to fetch.
            page_size: Number of items per page.
            validate: Whether to validate each row with Pydantic.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Paginated result containing collection ``MediaRecord`` items.
        """

        collection_pk = self._intermediate_collection_pk(project_pk, collection_pk) or collection_pk
        endpoint = self.endpoint.format(project_pk=str(project_pk))

        q = dict(query or {})
        q["collection"] = collection_pk

        return self.get(query=q, page=page, page_size=page_size, validate=validate,overwrite_endpoint=endpoint, **kwargs)

    def where_collection_media(
        self,
        project_pk: int,
        collection_pk: int,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        **kwargs,
    ) -> APIQuery:
        """Return a lazy iterator over collection media rows.

        Args:
            project_pk: Classification project primary key.
            collection_pk: Collection primary key used for filtering.
            query: Base query parameters.
            page_size: Number of items requested per API page.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Lazy ``APIQuery`` iterator yielding collection media rows.
        """

        collection_pk = self._intermediate_collection_pk(project_pk, collection_pk) or collection_pk
        endpoint = self.endpoint.format(project_pk=str(project_pk))

        q = dict(query or {})
        q["collection"] = collection_pk

        return self.where(query=q, page_size=page_size,overwrite_endpoint=endpoint, **kwargs)


    def export_collection_media(
        self,
        project_pk: int,
        collection_pk: int,
        query: Dict[str, Any] | None = None,
        file: str | Path | None = None,
        validate: bool = True,
        **kwargs,
    ) -> Path | List[BaseModel]:
        """Export all media rows for a collection in a project to CSV.

        Args:
            project_pk: Classification project primary key.
            collection_pk: Collection primary key used for filtering.
            query: Base query parameters.
            file: Output CSV file path. If ``None``, a temp file is created.
            validate: If ``True``, validates rows before writing CSV.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Path to the generated CSV file.
        """
        collection_pk = self._intermediate_collection_pk(project_pk, collection_pk) or collection_pk
        endpoint = self.endpoint.format(project_pk=str(project_pk))

        q = dict(query or {})
        q["collection"] = collection_pk

        return self.export(query=q, file=file,validate=validate,overwrite_endpoint=endpoint, **kwargs)

    def download_media_file(
        self,
        media_id: int,
        file_field: str = "file",
        file: str | Path | None = None,
        retry_attempts: int = 3,
        retry_min_wait: float = 0.5,
        retry_max_wait: float = 8.0,
    ) -> Path:
        """Download one media file with retry support.

        Args:
            media_id: Resource/media primary key used by the storage endpoint.
            file_field: Media field name (for example: ``file``, ``pfile``,
                ``tfile``, ``efile``).
            file: Output file path. If ``None``, a temp file is created.
            retry_attempts: Maximum number of attempts for transient failures.
            retry_min_wait: Minimum exponential backoff delay in seconds.
            retry_max_wait: Maximum exponential backoff delay in seconds.

        Returns:
            Path to the downloaded media file.
        """
        endpoint = f"storage/api/resource/media/{media_id}/{file_field}/"
        output_path = self.client._select_file(file)

        @retry(
            reraise=True,
            stop=stop_after_attempt(retry_attempts),
            wait=wait_exponential(multiplier=1, min=retry_min_wait, max=retry_max_wait),
            retry=retry_if_exception_type(Exception),
        )
        def _download_once() -> Path:
            response = self.client.make_request(endpoint=endpoint, method="GET", raise_on_error=True)
            output_path.write_bytes(response.content)
            return output_path

        return _download_once()

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
        **kwargs,
    ) -> list[Path]:
        """Download all media files for one classification project.

        Supports optional parallel downloads, retry strategy per file, and
        optional ZIP compression of downloaded files.

        Args:
            project_pk: Classification project primary key.
            output_dir: Directory where files are stored. Defaults to current dir.
            query: Base query parameters used to filter source media rows.
            parallel: Whether to enable threaded parallel downloads.
            max_workers: Maximum worker threads when ``parallel`` is enabled.
            compress: Whether to create a ZIP archive from downloaded files.
            archive_file: Target ZIP path when ``compress=True``. If ``None``,
                a default archive name is generated.
            retry_attempts: Maximum number of attempts per file download.
            retry_min_wait: Minimum exponential backoff delay in seconds.
            retry_max_wait: Maximum exponential backoff delay in seconds.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            List of downloaded file paths.
        """
        q = self._merge_query(query, kwargs)
        endpoint = self.endpoint.replace("{project_pk}", str(project_pk))
        data = self.client.get_all(endpoint, query=q)
        result = self._to_paginated(data, validate=False)

        output_path = Path(output_dir or ".")
        output_path.mkdir(parents=True, exist_ok=True)

        media_ids = [media_id for media_id in (self._extract_media_id(row) for row in result.results) if media_id]

        downloaded_files: list[Path] = []

        def _download_one(media_id: int) -> Path:
            return self.download_media_file(
                media_id=media_id,
                file_field="file",
                file=output_path / f"media_{media_id}",
                retry_attempts=retry_attempts,
                retry_min_wait=retry_min_wait,
                retry_max_wait=retry_max_wait,
            )

        if parallel and len(media_ids) > 1:
            workers = max(1, min(max_workers, len(media_ids)))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(_download_one, media_id) for media_id in media_ids]
                for future in as_completed(futures):
                    try:
                        downloaded_files.append(future.result())
                    except Exception:
                        continue
        else:
            for media_id in media_ids:
                try:
                    downloaded_files.append(_download_one(media_id))
                except Exception:
                    continue

        if compress and downloaded_files:
            if archive_file is None:
                archive_file = output_path / f"project_{project_pk}_media.zip"
            self._compress_files(downloaded_files, archive_file=archive_file)

        return downloaded_files

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
        **kwargs,
    ) -> list[Path]:
        """Download all media files for one collection within a project.

        Supports optional parallel downloads, retry strategy per file, and
        optional ZIP compression of downloaded files.

        Args:
            project_pk: Classification project primary key.
            collection_pk: Collection primary key used for filtering.
            output_dir: Directory where files are stored. Defaults to current dir.
            query: Base query parameters used to filter source media rows.
            parallel: Whether to enable threaded parallel downloads.
            max_workers: Maximum worker threads when ``parallel`` is enabled.
            compress: Whether to create a ZIP archive from downloaded files.
            archive_file: Target ZIP path when ``compress=True``. If ``None``,
                a default archive name is generated.
            retry_attempts: Maximum number of attempts per file download.
            retry_min_wait: Minimum exponential backoff delay in seconds.
            retry_max_wait: Maximum exponential backoff delay in seconds.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            List of downloaded file paths.
        """
        q = self._merge_query(query, kwargs)
        q = dict(q or {})
        q.setdefault("collection", collection_pk)

        endpoint = self.endpoint.replace("{project_pk}", str(project_pk))
        data = self.client.get_all(endpoint, query=q)
        result = self._to_paginated(data, validate=False)

        output_path = Path(output_dir or ".")
        output_path.mkdir(parents=True, exist_ok=True)

        media_ids = [media_id for media_id in (self._extract_media_id(row) for row in result.results) if media_id]

        downloaded_files: list[Path] = []

        def _download_one(media_id: int) -> Path:
            return self.download_media_file(
                media_id=media_id,
                file_field="file",
                file=output_path / f"media_{media_id}",
                retry_attempts=retry_attempts,
                retry_min_wait=retry_min_wait,
                retry_max_wait=retry_max_wait,
            )

        if parallel and len(media_ids) > 1:
            workers = max(1, min(max_workers, len(media_ids)))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(_download_one, media_id) for media_id in media_ids]
                for future in as_completed(futures):
                    try:
                        downloaded_files.append(future.result())
                    except Exception:
                        continue
        else:
            for media_id in media_ids:
                try:
                    downloaded_files.append(_download_one(media_id))
                except Exception:
                    continue

        if compress and downloaded_files:
            if archive_file is None:
                archive_file = output_path / f"project_{project_pk}_collection_{collection_pk}_media.zip"
            self._compress_files(downloaded_files, archive_file=archive_file)

        return downloaded_files


    def _intermediate_collection_pk(self, cp_pk:int, collection_pk:int) -> int:
        cp_c_c: ClassificationProjectsCollectionsComponent = ClassificationProjectsCollectionsComponent(self.client)
        cp_c = cp_c_c.get_all_classification_project(project_pk=cp_pk)

        for collection in cp_c.results:
            if collection.collection_pk == collection_pk:
                collection_pk = collection.pk
                break

        return collection_pk