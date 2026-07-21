"""
Component for the /api/locations/ resource.
"""

from __future__ import annotations

import time
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Dict

from tenacity import Retrying

from trapper_client import err
from trapper_client.components.base import TrapperComponent
from trapper_client.csv_chunking import DEFAULT_MAX_CHUNK_BYTES, split_csv_by_size
from trapper_client.retry_utils import retrying_for_chunk_upload
from trapper_client.schemas import Location, LocationExport


class LocationsComponent(TrapperComponent[Location]):
    """
    Component for the ``/geomap/api/locations/`` resource.

    Retrieve, filter, and export location data from Trapper.

    Main endpoints:
    - ``GET /geomap/api/locations``: (listado, paginado y filtrable por query params)
    - ``GET /geomap/api/locations/{id}``: (detalle de una localización)
    - ``GET /geomap/api/locations/export/	``: (exportar a CSV, con filtros por query params)

    ``import_locations()`` is different from the rest of this component: the
    REST API is read-only for locations, so it simulates the classic web UI's
    ``geomap/location/import/`` form via cookie/session auth instead
    (see :meth:`~trapper_client.api_client_base.APIClientBase.session_login`).

    **Available filter fields:**

    |------------------|-------------|-------------|
    | Parameter        | Type        | Description |
    |------------------|-------------|-------------|
    | name	           | string      | Partial search (case-insensitive) contains on location name
    | description      | string      | Partial search (case-insensitive) contains on description
    | owner	           | boolean     | true = only locations owned by the current user
    | owners	       | list of PKs | Filter by one or more users (by PK)
    | research_project | list of PKs | Filter by one or more research projects (by PK)
    | locations_map	   | list of PKs | Filter by locations associated to a map
    | deployments	   | list of PKs | Filter locations that have those deployments
    | search           | string      | Global text search across location_id, name, description, county, city, owner username

    **Examples:**

        # Retrieve all locations
        for loc in client.locations.all():
            print(loc)

        # Filter by research project
        for loc in client.locations.where(research_project=1):
            print(loc)

        # Filter by owner and search text
        for loc in client.locations.where(owner=True, search="camera"):
            print(loc)

        # Export all locations to CSV
        client.locations.export(file="/tmp/locations.csv")

        # Export filtered results to CSV
        client.locations.export(query={"research_project": 5}, file="/tmp/project5_locations.csv")
    """

    endpoint = "/geomap/api/locations"
    export_endpoint = "/geomap/api/locations/export/"
    schema = Location
    export_schema = LocationExport

    import_endpoint = "geomap/location/import/"

    def import_locations(
        self,
        file: str | Path,
        research_project: int | str,
        timezone: str,
        gpx_file: str | Path | None = None,
        ignore_dst: bool = False,
        split: bool = False,
        delay: float = 1.0,
        chunk_size: int = DEFAULT_MAX_CHUNK_BYTES,
        retry_attempts: int = 3,
        retry_min_wait: float = 1.0,
        retry_max_wait: float = 10.0,
        raise_on_error: bool = True,
    ) -> bool:
        """Import locations from a CSV (and optionally a companion GPX) file.

        The locations REST API is read-only, so this simulates the classic
        Trapper web UI's ``geomap/location/import/`` form instead — a plain
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
        failures (e.g. a ``locationID`` that already exists), when present.
        It still can't turn that into a structured report object the way
        :meth:`ClassificationsComponent.import_classifications` does for its
        proper REST endpoint — you get a joined string of messages.

        Warning:
            This is a workaround, not a stable integration: it depends on an
            unversioned HTML form (``geomap/location/import/``) rather than a
            documented API contract, so a Trapper change to that page (field
            names, added steps, a different success/failure response) can
            break it silently. Prefer
            :meth:`ClassificationsComponent.import_classifications` (a real,
            token-authenticated REST endpoint) as the model for what a
            properly supported import should look like, if the server ever
            exposes one for locations too.

        Args:
            file: Path to the locations CSV file (comma-separated).
            research_project: Research project PK to attach imported locations
                to. The server's ``LocationImportForm`` declares this field
                ``required=False`` but its ``clean_research_project()``
                rejects a missing value — it's required in practice, so this
                method requires it too rather than letting the server reject
                it with a 200 (form re-render), which is easy to mistake for
                success if you're only checking the status code.
            timezone: IANA timezone name applied to all imported locations
                (e.g. ``"Europe/Madrid"``). The server form declares this
                optional too, but the importer persists locations via
                ``Location.objects.bulk_create()`` — which skips normal model
                validation — so an omitted/blank timezone can silently create
                locations with an invalid ``timezone`` value instead of
                failing loudly. That bad value can then crash *any* later
                request that serializes those rows (list/filter endpoints,
                the web UI's own location list) with an unrelated-looking
                500, long after the import "succeeded". This method requires
                it to avoid creating that kind of latent, hard-to-diagnose
                server-side corruption.
            gpx_file: Optional path to a companion GPX file. Not compatible
                with ``split=True`` (the server form rejects a request
                carrying both a CSV and a GPX file anyway, and splitting only
                makes sense for the CSV path).
            ignore_dst: Whether camera traps at these locations ignore
                Daylight Saving Time.
            split: Instead of uploading ``file`` in one request, split it
                into several smaller, self-contained CSV chunks (each
                repeating the header row) and import them one request at a
                time, sleeping ``delay`` seconds between uploads. There is no
                real chunked/resumable upload protocol on this endpoint (see
                :mod:`trapper_client.csv_chunking`) — this is a workaround
                for servers that reject or time out on very large single-file
                uploads, not a faster or more efficient way to import.
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
                :meth:`~trapper_client.api_client_base.APIClientBase.session_login`),
                or if ``split=True`` is combined with ``gpx_file``.

        Example::

            client.locations.import_locations(
                file="/tmp/locations.csv",
                research_project=7,
                timezone="Europe/Madrid",
            )

            # A very large CSV, uploaded in <=512 KiB chunks, 2s apart:
            client.locations.import_locations(
                file="/tmp/huge_locations.csv",
                research_project=7,
                timezone="Europe/Madrid",
                split=True,
                delay=2,
            )
        """
        if split and gpx_file is not None:
            raise ValueError("split=True is not supported together with gpx_file")

        data: Dict[str, Any] = {
            "research_project": research_project,
            "timezone": timezone,
            "ignore_DST": ignore_dst,
        }

        retrying = retrying_for_chunk_upload(retry_attempts, retry_min_wait, retry_max_wait)

        if not split:
            return self._import_locations_once(
                data, csv_file=Path(file), gpx_file=gpx_file,
                raise_on_error=raise_on_error, retrying=retrying,
            )

        chunk_paths = split_csv_by_size(file, max_bytes=chunk_size)
        try:
            all_ok = True
            for i, chunk_path in enumerate(chunk_paths):
                ok = self._import_locations_once(
                    data, csv_file=chunk_path, gpx_file=None,
                    raise_on_error=raise_on_error, retrying=retrying,
                )
                all_ok = all_ok and ok
                if i < len(chunk_paths) - 1:
                    time.sleep(delay)
            return all_ok
        finally:
            for chunk_path in chunk_paths:
                chunk_path.unlink(missing_ok=True)

    def _import_locations_once(
        self,
        data: Dict[str, Any],
        csv_file: Path,
        gpx_file: str | Path | None,
        raise_on_error: bool,
        retrying: Retrying,
    ) -> bool:
        """Perform one ``geomap/location/import/`` POST for a single CSV file."""
        files: Dict[str, Any] = {}
        handles = []
        with ExitStack() as stack:
            fh = stack.enter_context(csv_file.open("rb"))
            files["csv_file"] = (csv_file.name, fh, "text/csv")
            handles.append(fh)

            if gpx_file is not None:
                gpx_path = Path(gpx_file)
                gpx_fh = stack.enter_context(gpx_path.open("rb"))
                files["gpx_file"] = (gpx_path.name, gpx_fh, "application/gpx+xml")
                handles.append(gpx_fh)

            def _do_request():
                # Rewind before every attempt: a retry re-sends the same file
                # object(s), whose read position may have advanced past a
                # partial read from a prior attempt that timed out mid-upload.
                for handle in handles:
                    handle.seek(0)
                return self.client.session_post_multipart(
                    self.import_endpoint, data=data, files=files,
                )

            response = retrying(_do_request)

        if response.status_code == 302:
            return True

        if raise_on_error:
            message = self.client._extract_html_error_text(response.text)
            raise err.APIError(
                f"Location import failed (status {response.status_code}): {message}"
            )
        return False
