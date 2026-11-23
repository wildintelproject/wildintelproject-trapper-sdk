"""
Component for the /api/deployments/ resource.
"""

from __future__ import annotations

import math
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import date
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, Literal, Mapping

from tenacity import Retrying

from trapper_client import err
from trapper_client.api_query import APIQuery
from trapper_client.components.base import TrapperComponent
from trapper_client.components.locations import LocationsComponent
from trapper_client.components.resources import DownloadReport, ResourcesComponent, safe_filename
from trapper_client.csv_chunking import DEFAULT_MAX_CHUNK_BYTES, split_csv_by_size
from trapper_client.retry_utils import retrying_for_chunk_upload
from trapper_client.schemas import Deployment, DeploymentExport


class DeploymentsComponent(TrapperComponent[Deployment]):
    """
    Component for the ``/geomap/api/deployments`` resource.

    **Available endpoints:**

    - ``GET /geomap/api/deployments``: Paginated list of deployments
    - ``GET /geomap/api/deployments/{pk}``: Retrieve a single deployment by ID
    - ``GET /geomap/api/deployments/export/``: Export deployments to CSV (gzipped)

    **Available filter parameters:**

    - ``location`` (int or list): Filter by location ID(s)
    - ``research_project`` (int or list): Filter by research project ID(s)
    - ``tags`` (int or list): Filter by tag ID(s)
    - ``owner`` (bool): Filter by current user ownership (True/False)
    - ``sdate_from``, ``sdate_to`` (date): Filter by start date range (ISO format)
    - ``edate_from``, ``edate_to`` (date): Filter by end date range (ISO format)
    - ``classification_project`` (int): Filter by classification project ID
    - ``correct_setup`` (bool): Filter by setup correctness
    - ``correct_tstamp`` (bool): Filter by timestamp correctness
    - ``search`` (str): Search in deployment_id or owner__username

    There is no collection filter: Trapper's deployment API has none (any
    unknown parameter, such as ``colls``, is silently ignored and every
    deployment comes back). Use :meth:`by_collection` instead.

    **Examples:**

        # Deployments with images in collection 5, among research project 3's
        for dep in client.deployments.by_collection(5, research_project=3):
            print(dep)

        # Filter by location and date range
        for dep in client.deployments.where(location=42, sdate_from="2024-01-01"):
            print(dep)

        # Export to CSV
        client.deployments.export_by_collection(5, research_project=3, file="/tmp/deps.csv")

    ``import_deployments()`` is different from the rest of this component: the
    REST API is read-only for deployments, so it simulates the classic web
    UI's ``geomap/deployment/import/`` form via cookie/session auth instead
    (see :meth:`~trapper_client.api_client_base.APIClientBase.session_login`).
    """

    endpoint = "geomap/api/deployments"

    # Checked against live Trapper v1 and v2: a parameter that is not here is ignored by the server.
    _V1_FILTERS = frozenset({
        "pk", "location", "research_project", "tags", "owner", "sdate_from", "sdate_to", "edate_from",
        "edate_to", "classification_project", "correct_setup", "correct_tstamp", "search",
        "deployment_code", "deployment_id", "view_quality", "setup_by", "camera_id", "camera_model",
        "camera_interval", "camera_height", "camera_depth", "camera_tilt", "camera_heading",
        "detection_distance", "bait_type", "feature_type", "habitat", "session", "array", "comments",
        "date_created", "managers", "start_date", "end_date", "is_incomplete", "capture_method", "status",
    })
    known_filters = {
        "v1": _V1_FILTERS,
        "v2": _V1_FILTERS | {"in_bbox"},  # v2 only: v1's list ignores it
    }
    export_endpoint = "geomap/api/deployments/export/"
    schema = Deployment
    export_schema = DeploymentExport

    #: How many location pks go in one request of :meth:`in_area` (the list of pks is in the URL).
    in_area_batch_size = 50

    def in_area(
        self,
        bbox: tuple[float, float, float, float] | None = None,
        center: tuple[float, float] | None = None,
        radius: float | None = None,
        **filters: Any,
    ) -> Iterator[Deployment]:
        """Iterate over the deployments whose location is inside an area.

        A deployment has no coordinates of its own: they are its location's, and the deployment list gives
        only the location's pk. So this finds the locations in the area with
        :meth:`LocationsComponent.in_area <trapper_client.components.locations.LocationsComponent.in_area>`
        (reading every location the account can see, filtered on the client) and then asks for the
        deployments of those locations, ``in_area_batch_size`` pks per request. A deployment whose location
        has no readable coordinates is left out.

        Args:
            bbox: ``(min_lon, min_lat, max_lon, max_lat)``, edges included. ``min_lon > max_lon`` crosses
                the antimeridian.
            center: ``(longitude, latitude)`` of the circle, longitude first, like Trapper.
            radius: Radius of the circle in **metres**; needs ``center``.
            **filters: Any filter of :meth:`where` (``research_project``, ``sdate_from``, ``tags``, ...),
                applied to the deployments, not to the locations.

        Raises:
            ValueError: if the area is wrong (see :meth:`LocationsComponent.in_area`), before any request
                for deployments. A ``location`` filter cannot be combined with the area.

        Example:
            ``client.deployments.in_area(center=(-6.44, 37.05), radius=5000, research_project=3)``
        """
        if "location" in filters:
            raise ValueError("in_area() chooses the locations itself: do not pass `location`")
        locations = LocationsComponent(self.client).in_area(bbox=bbox, center=center, radius=radius)
        pks = sorted(location.pk for location in locations)
        size = max(1, int(self.in_area_batch_size))

        def deployments() -> Iterator[Deployment]:
            for start in range(0, len(pks), size):
                yield from self.where(location=pks[start:start + size], **filters)

        return deployments()

    import_endpoint = "geomap/deployment/import/"
    #: Trapper v2 moved the import forms into the Django admin.
    import_endpoint_v2 = "admin/geomap/deployment/import-deployments/"

    def import_deployments(
        self,
        file: str | Path,
        timezone: str,
        research_project: int | str,
        classification_project: int | str | None = None,
        update: bool = False,
        create_locations: bool = False,
        ignore_dst: bool = False,
        split: bool = False,
        delay: float = 1.0,
        chunk_size: int = DEFAULT_MAX_CHUNK_BYTES,
        retry_attempts: int = 3,
        retry_min_wait: float = 1.0,
        retry_max_wait: float = 10.0,
        raise_on_error: bool = True,
    ) -> bool:
        """Import deployments from a CSV file.

        The deployments REST API is read-only, so this simulates the classic
        Trapper web UI's ``geomap/deployment/import/`` form instead — a plain
        Django ``FormView`` behind ``LoginRequiredMixin``, authenticated with
        cookies/CSRF rather than the API's token auth (see
        :meth:`~trapper_client.api_client_base.APIClientBase.session_login`).
        Requires ``user_name``/``user_password`` to be configured on the
        client, with ``user_name`` set to the account's *email* address
        (this server only accepts email as the login identifier).

        Because this is a server-rendered HTML view, not a JSON API, failure
        details (invalid columns, bad rows, ...) come back embedded in an
        HTML error page rather than structured data — this method does a
        best-effort extraction of the error text (see
        :meth:`~trapper_client.api_client_base.APIClientBase._extract_html_error_text`),
        including the per-row/per-field validation messages from the
        frictionless report the server embeds as JSON for CSV-structure
        failures (e.g. a ``deploymentID``/``locationID`` that already
        exists), when present. It still can't turn that into a structured
        report object the way :meth:`ClassificationsComponent.import_classifications`
        does for its proper REST endpoint — you get a joined string of messages.

        On Trapper v2 the form is the import action of the Django admin
        (``admin/geomap/deployment/import-deployments/``); the same arguments apply. The account must be a
        staff user with the add permission, and the server imports
        asynchronously, so ``True`` means the table was validated and queued.

        Warning:
            This is a workaround, not a stable integration: it depends on an
            unversioned HTML form (``geomap/deployment/import/``) rather than
            a documented API contract, so a Trapper change to that page
            (field names, added steps, a different success/failure response)
            can break it silently. Prefer
            :meth:`ClassificationsComponent.import_classifications` (a real,
            token-authenticated REST endpoint) as the model for what a
            properly supported import should look like, if the server ever
            exposes one for deployments too.

        Args:
            file: Path to the deployments CSV file (comma-separated).
            timezone: IANA timezone name used to process each deployment's
                ``start``/``end`` timestamps (e.g. ``"Europe/Madrid"``).
                Required by the server form (unlike locations, there is no
                default here).
            research_project: Research project PK to attach imported
                deployments to. The server's ``DeploymentImportForm`` declares
                this field ``required=False`` but its
                ``clean_research_project()`` rejects a missing value — it's
                required in practice, so this method requires it too rather
                than letting the server reject it with a 200 (form
                re-render), which is easy to mistake for success if you're
                only checking the status code.
            classification_project: Optional classification project PK to
                link all imported deployments to.
            update: Update existing deployments instead of creating new ones.
                Requires an ``_id`` column with existing PKs in the CSV.
            create_locations: Auto-create locations referenced by the CSV.
                Requires ``locationID``, ``longitude``, and ``latitude``
                columns in the CSV.
            ignore_dst: Whether camera traps at locations created by this
                import ignore Daylight Saving Time.
            split: Instead of uploading ``file`` in one request, split it
                into several smaller, self-contained CSV chunks (each
                repeating the header row) and import them one request at a
                time, sleeping ``delay`` seconds between uploads. There is no
                real chunked/resumable upload protocol on this endpoint (see
                :mod:`trapper_client.csv_chunking`) — this is a workaround
                for servers that reject or time out on very large single-file
                uploads, not a faster or more efficient way to import.

                Caution with ``create_locations=True``: each chunk is
                imported as an independent request, so if the same
                ``locationID`` appears in more than one chunk, the server
                will attempt to create that location again in each chunk
                that references it — it does not know about locations
                created by a previous chunk. Only combine ``split`` with
                ``create_locations`` if you know each ``locationID`` in the
                file falls within a single chunk, or pre-create the
                locations separately and import with
                ``create_locations=False`` instead.
            delay: Seconds to sleep between chunk uploads when ``split=True``.
                Ignored otherwise.
            chunk_size: Maximum size in bytes of each chunk when ``split=True``.
                Ignored otherwise. Defaults to 512 KiB.
            retry_attempts: Maximum number of attempts (first try + retries)
                per chunk/file upload when the request fails with a
                network-level error (read timeout, connection reset, ...) —
                the failure mode expected when a chunk is still too large or
                slow for the server. Does not retry on HTTP error responses
                (those are validation failures a retry can't fix). Set to
                ``1`` to disable retrying.
            retry_min_wait: Minimum exponential backoff delay in seconds
                between retry attempts.
            retry_max_wait: Maximum exponential backoff delay in seconds
                between retry attempts.
            raise_on_error: Whether to raise when the server doesn't confirm
                success (i.e. the response isn't the expected redirect). With
                ``split=True``, raises as soon as one chunk fails rather than
                uploading the rest.

        Returns:
            ``True`` on success (the server responds with a redirect, as the
            classic UI does after a successful import — for every chunk, when
            ``split=True``). ``False`` when ``raise_on_error=False`` and the
            import (or, with ``split=True``, any one chunk of it) did not
            succeed.

        Raises:
            err.APIError: If the import fails and ``raise_on_error=True``.
            ValueError: If session credentials are not configured (see
                :meth:`~trapper_client.api_client_base.APIClientBase.session_login`).

        Example::

            client.deployments.import_deployments(
                file="/tmp/deployments.csv",
                timezone="Europe/Madrid",
                research_project=7,
                create_locations=True,
            )

            # A very large CSV, uploaded in <=512 KiB chunks, 2s apart:
            client.deployments.import_deployments(
                file="/tmp/huge_deployments.csv",
                timezone="Europe/Madrid",
                research_project=7,
                split=True,
                delay=2,
            )
        """
        data: Dict[str, Any] = {
            "timezone": timezone,
            "research_project": research_project,
            "update": update,
            "create_locations": create_locations,
            "ignore_DST": ignore_dst,
        }
        if classification_project is not None:
            data["classification_project"] = classification_project

        retrying = retrying_for_chunk_upload(retry_attempts, retry_min_wait, retry_max_wait)

        if not split:
            return self._import_deployments_once(
                data, csv_file=Path(file), raise_on_error=raise_on_error, retrying=retrying,
            )

        chunk_paths = split_csv_by_size(file, max_bytes=chunk_size)
        try:
            all_ok = True
            for i, chunk_path in enumerate(chunk_paths):
                ok = self._import_deployments_once(
                    data, csv_file=chunk_path, raise_on_error=raise_on_error, retrying=retrying,
                )
                all_ok = all_ok and ok
                if i < len(chunk_paths) - 1:
                    time.sleep(delay)
            return all_ok
        finally:
            for chunk_path in chunk_paths:
                chunk_path.unlink(missing_ok=True)

    def _import_deployments_once(
        self,
        data: Dict[str, Any],
        csv_file: Path,
        raise_on_error: bool,
        retrying: Retrying,
    ) -> bool:
        """Perform one ``geomap/deployment/import/`` POST for a single CSV file."""
        with ExitStack() as stack:
            fh = stack.enter_context(csv_file.open("rb"))
            files = {"csv_file": (csv_file.name, fh, "text/csv")}

            def _do_request():
                # Rewind before every attempt: a retry re-sends the same file
                # object, whose read position may have advanced past a
                # partial read from a prior attempt that timed out mid-upload.
                fh.seek(0)
                return self._import_post(data, files)

            response = retrying(_do_request)

        if self._import_accepted(response):
            return True

        if raise_on_error:
            raise self._import_error("Deployment", response)
        return False

    geojson_endpoint = "api/deployments/geojson/"

    def geojson(
        self,
        classification_project: int | None = None,
        observation_type: str | list[str] | None = None,
        species: int | str | list[int | str] | None = None,
        start_date_gte: str | date | None = None,
        end_date_lte: str | date | None = None,
        refresh: bool = False,
        query: Dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Deployments as a GeoJSON ``FeatureCollection`` (**Trapper v2 only**).

        Replaces ``client.maps`` and ``client.locations_geojson``, which v2 removed. Each feature is a
        point whose ``properties`` follow the Camtrap DP shape (``deploymentID``, ``locationName``,
        ``deploymentStart``, ...). Only deployments the current user can access are returned.

        Args:
            classification_project: Keep deployments linked to this classification project, and
                scope ``observation_type`` / ``species`` to its classifications.
            observation_type: One value or a list (``"animal"``, ``["animal", "human"]``): keep
                deployments with at least one classification of that type.
            species: One species primary key or a list: keep deployments where it was classified.
            start_date_gte: Deployments that start on or after this date (``YYYY-MM-DD``).
            end_date_lte: Deployments that end on or before this date.
            refresh: Bypass the server's one-hour cache for this query and rebuild it.
            query: Extra query parameters.

        Returns:
            The GeoJSON payload as a ``dict``.

        Raises:
            err.UnsupportedVersionError: On Trapper v1 (use ``client.locations_geojson`` there).

        Example::

            fc = client.deployments.geojson(classification_project=2, species=[3, 7])
            for feature in fc["features"]:
                lon, lat = feature["geometry"]["coordinates"]
                print(feature["properties"]["deploymentID"], lon, lat)
        """
        self._require_version("v2", feature="deployments.geojson (api/deployments/geojson/)")

        def csv(value: Any) -> Any:
            return ",".join(str(v) for v in value) if isinstance(value, (list, tuple, set)) else value

        q = dict(query or {})
        q.update(kwargs)
        for key, value in {
            "classification_project": classification_project,
            "observation_type": csv(observation_type),
            "species": csv(species),
            "start_date_gte": start_date_gte.isoformat() if isinstance(start_date_gte, date) else start_date_gte,
            "end_date_lte": end_date_lte.isoformat() if isinstance(end_date_lte, date) else end_date_lte,
        }.items():
            if value is not None:
                q[key] = value
        if refresh:
            q["refresh"] = 1
        return self._unwrap_feature_collection(self.client.get(self.geojson_endpoint, query=q))

    def by_collection_with_counts(
        self,
        collection_id: int,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        max_workers: int = 8,
        **kwargs: Any,
    ) -> list[tuple[Deployment, int]]:
        """Deployments with at least one resource in a collection, each with
        how many resources it has there.

        Trapper's deployment API can't filter by collection, but its
        resource API can filter by collection AND deployment at once — so
        every candidate deployment (whatever :meth:`where` returns for
        ``query``/``kwargs``) is checked with one single-item resource
        request, ``max_workers`` of them at a time. Narrow the candidates
        (``research_project=...`` is the usual one): with no filter, every
        deployment on the server is checked.

        Args:
            collection_id: Collection primary key (the storage collection's
                own pk — ``collection_pk`` in a classification project's
                collection list).
            query: Base query parameters for the candidate deployments.
            page_size: Page size used to list the candidates.
            max_workers: How many resource requests run in parallel.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            ``(deployment, resource count)`` pairs, in candidate order.
        """
        candidates = list(self.where(query=query, page_size=page_size, **kwargs))

        def resources_in_collection(deployment: Deployment) -> int:
            data = self.client.get(
                ResourcesComponent.endpoint,
                query={"collections": collection_id, "deployments": deployment.pk, "page_size": 1},
            )
            return int((data.get("pagination") or {}).get("count") or 0)

        with ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
            counts = list(pool.map(resources_in_collection, candidates))
        return [(deployment, count) for deployment, count in zip(candidates, counts) if count]

    def by_collection(
        self,
        collection_id: int,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        max_workers: int = 8,
        **kwargs: Any,
    ) -> list[Deployment]:
        """Deployments with at least one resource in a collection — see
        :meth:`by_collection_with_counts`, which this wraps (and whose
        advice about narrowing the candidates applies here too).

        Returns:
            The matching deployments, in candidate order.
        """
        return [
            deployment
            for deployment, _ in self.by_collection_with_counts(
                collection_id, query=query, page_size=page_size, max_workers=max_workers, **kwargs,
            )
        ]

    def export_by_collection(
        self,
        collection_id: int,
        query: Dict[str, Any] | None = None,
        file: str | Path | None = None,
        max_workers: int = 8,
        **kwargs: Any,
    ) -> Path | list[DeploymentExport]:
        """Export the deployments with at least one resource in a collection.

        Exports the candidate deployments (``query``/``kwargs``, same as
        :meth:`by_collection`) and keeps only those :meth:`by_collection`
        finds in the collection.

        Args:
            collection_id: Collection primary key.
            query: Base query parameters for the candidate deployments.
            file: Output CSV file path. If ``None``, returns a list of models.
            max_workers: How many resource requests run in parallel.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            ``Path`` to the generated CSV when ``file`` is provided,
            otherwise ``list[DeploymentExport]``.
        """
        in_collection = {
            deployment.pk
            for deployment in self.by_collection(collection_id, query=query, max_workers=max_workers, **kwargs)
        }
        rows = [row for row in self.export(query=query, file=None, **kwargs) if row.pk in in_collection]
        if file is None:
            return rows
        output_path = self.client._select_file(file)
        self.client._write_csv([row.model_dump(mode="json") for row in rows], output_path)
        return output_path

    def download_resources(
        self,
        deployment_pk: int,
        directory: str | Path,
        kind: Literal["original", "preview", "thumbnail"] = "original",
        filter_fn: Callable[[Any], bool] | None = None,
        skip_existing: bool = True,
        on_error: Literal["continue", "raise"] = "continue",
        progress_callback: Callable[[str, Dict[str, Any]], None] | None = None,
        retry_attempts: int = 3,
        retry_min_wait: float = 1.0,
        retry_max_wait: float = 10.0,
        **filters: Any,
    ) -> DownloadReport:
        """Download the files of the resources of a deployment into ``<directory>/<deployment_id>/``.

        The resources of the deployment are listed with ``resources.where(deployments=deployment_pk, **filters)`` and each one is
        saved with :meth:`ResourcesComponent.download` (see :meth:`ResourcesComponent.download_many` for the file names,
        the report and the errors): a file that is already in the folder is skipped, so a run can be repeated, and a
        failure does not stop the others. Needs ``user_name`` and ``user_password``.

        Args:
            deployment_pk: Deployment primary key. (It is not called ``pk`` because ``pk`` is also a filter of the resource
                list, which this method passes on: ``pk=[1, 2]`` chooses resources.)
            directory: Where the folder of the deployment goes.
            kind: ``"original"``, ``"preview"`` or ``"thumbnail"``.
            filter_fn: ``predicate(resource) -> bool`` applied on the client to choose which resources, for what the
                server cannot filter (``lambda r: r.date_recorded.hour < 6``).
            skip_existing: Leave alone the files that are already there.
            on_error: ``"continue"`` (default) or ``"raise"`` at the first failure.
            progress_callback: ``callback(event, data)`` for each file (see :meth:`ResourcesComponent.download_many`).
            retry_attempts: Attempts per file (see :meth:`ResourcesComponent.download`).
            retry_min_wait: Minimum backoff in seconds.
            retry_max_wait: Maximum backoff in seconds.
            **filters: Any filter of the resource list: ``resource_type``, ``status``, ``rdate_from``/``rdate_to``,
                ``rtime_from``/``rtime_to``, ``tags``, ``species``, ``observation_type``, ``timestamp_error``,
                ``search``, ... (see ``client.resources``).

        Returns:
            A :class:`~trapper_client.components.resources.DownloadReport`.

        Example::

            report = client.deployments.download_resources(
                12, "downloads/", rdate_from="2024-03-01", rdate_to="2024-03-31", resource_type="I",
            )
            print(report)                     # 40 downloaded, 0 already there, 0 failed, in downloads/don01-2024a
        """
        if "deployments" in filters:
            raise ValueError("download_resources() chooses the deployment itself: do not pass `deployments`")
        deployment = self.find(deployment_pk)
        folder = Path(directory) / safe_filename(deployment.deployment_id, fallback=f"deployment-{deployment_pk}")
        resources = ResourcesComponent(self.client)
        total = None if filter_fn else resources.get(page_size=1, deployments=deployment_pk, **filters).pagination.count
        return resources.download_many(
            resources.where(deployments=deployment_pk, filter_fn=filter_fn, page_size=100, **filters), folder, kind=kind,
            skip_existing=skip_existing, on_error=on_error, progress_callback=progress_callback, total=total,
            retry_attempts=retry_attempts, retry_min_wait=retry_min_wait, retry_max_wait=retry_max_wait,
        )

    def wait_for_import(
        self,
        deployment_ids: Iterable[str],
        timeout: float = 60.0,
        interval: float = 2.0,
        raise_on_timeout: bool = True,
    ) -> bool:
        """Wait until the imported deployments are visible through the API.

        Trapper v2 imports asynchronously: ``import_deployments()`` returning ``True`` only means the table was
        validated and queued. Neither version offers an API to query the import task, so this
        checks the outcome instead: it polls the list endpoint until every ID is there.

        Args:
            deployment_ids: The deployment IDs the import should create (the ``deploymentID`` column).
            timeout: Seconds to wait in total.
            interval: Seconds between polls.
            raise_on_timeout: Raise ``TimeoutError`` instead of returning ``False``.

        Returns:
            ``True`` once all of them exist; ``False`` on timeout when ``raise_on_timeout=False``.

        Raises:
            TimeoutError: Some IDs were still missing after ``timeout`` seconds.

        Example::

            client.deployments.import_deployments(file="deployments.csv", research_project=1, timezone="Europe/Madrid")
            client.deployments.wait_for_import(["DON01-2024A"])
        """
        return self._wait_for_ids(deployment_ids, "deployment_id", timeout, interval, raise_on_timeout, "deployment ID")

    def wait_for_update(
        self,
        changes: Mapping[str, Mapping[str, Any]],
        timeout: float = 60.0,
        interval: float = 2.0,
        raise_on_timeout: bool = True,
    ) -> bool:
        """Wait until an update import (``import_deployments(update=True)``) has been applied.

        ``import_deployments()`` returns ``True`` as soon as the table is validated and queued: the changes
        land a moment later, and :meth:`wait_for_import` cannot tell, because the IDs already exist. This
        polls the export until every deployment has the values you expect.

        Args:
            changes: ``{deployment_id: {field: expected value}}``, with the field names of
                :class:`~trapper_client.schemas.DeploymentExport` (``camera_height``, ``habitat``, ``tags``,
                ...). Numbers are compared with a tolerance. The ID is the stored one: Trapper slugifies the
                ``deploymentID`` of an import (``"Don 01"`` is stored as ``"don-01"``).
            timeout: Seconds to wait in total.
            interval: Seconds between polls.
            raise_on_timeout: Raise ``TimeoutError`` instead of returning ``False``.

        Returns:
            ``True`` once every deployment has every expected value; ``False`` on timeout when
            ``raise_on_timeout=False``.

        Raises:
            ValueError: If a field is not a field of ``DeploymentExport`` (before any request).
            TimeoutError: Some values were still different after ``timeout`` seconds.

        Example::

            client.deployments.import_deployments(file="edited.csv", research_project=1, timezone="Europe/Madrid", update=True)
            client.deployments.wait_for_update({"don01-2024a": {"camera_height": 1.25, "habitat": "dehesa"}})
        """
        known = DeploymentExport.model_fields
        for deployment_id, expected in changes.items():
            unknown = sorted(f for f in expected if f not in known)
            if unknown:
                raise ValueError(f"{deployment_id}: not a field of DeploymentExport: {', '.join(unknown)}")

        def same(actual: Any, wanted: Any) -> bool:
            if isinstance(actual, float) or isinstance(wanted, float):
                try:
                    return math.isclose(float(actual), float(wanted), rel_tol=1e-9, abs_tol=1e-9)
                except (TypeError, ValueError):
                    return False
            return actual == wanted

        pending = {str(i): dict(e) for i, e in changes.items()}
        deadline = time.monotonic() + timeout
        while True:
            for deployment_id in list(pending):
                try:
                    rows = self.export(file=None, search=deployment_id)
                except err.BadRequestError:       # Trapper answers an empty export with a 400
                    rows = []
                row = next((r for r in rows if r.deployment_id == deployment_id), None)
                if row is not None and all(same(getattr(row, f), v) for f, v in pending[deployment_id].items()):
                    del pending[deployment_id]
            if not pending:
                return True
            if time.monotonic() >= deadline:
                if raise_on_timeout:
                    raise TimeoutError(
                        f"{len(pending)} deployment(s) not updated after {timeout:g}s: {', '.join(list(pending)[:10])}"
                    )
                return False
            time.sleep(interval)
