"""
Component for the /api/deployments/ resource.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable

from tenacity import Retrying

from trapper_client import err
from trapper_client.api_query import APIQuery
from trapper_client.components.base import TrapperComponent
from trapper_client.components.resources import ResourcesComponent
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
    export_endpoint = "geomap/api/deployments/export/"
    schema = Deployment
    export_schema = DeploymentExport

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
