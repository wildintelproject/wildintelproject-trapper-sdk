"""
Component for the /api/locations/ resource.
"""

from __future__ import annotations

import time
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator

from tenacity import Retrying

from trapper_client import err
from trapper_client.components.base import TrapperComponent, versioned
from trapper_client.geo import distance_m, in_bbox
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

        # Locations inside a bounding box or a circle (filtered on the client)
        for loc in client.locations.in_area(center=(-6.44, 37.05), radius=5000):
            print(loc)

        # Export all locations to CSV
        client.locations.export(file="/tmp/locations.csv")

        # Export filtered results to CSV
        client.locations.export(query={"research_project": 5}, file="/tmp/project5_locations.csv")
    """

    endpoint = versioned("/geomap/api/locations", ninja="api/v2/locations/")

    # Checked against live Trapper v1 and v2: a parameter that is not here is ignored by the server.
    _V2_FILTERS = frozenset({
        "pk", "name", "description", "owner", "owners", "research_project", "deployments", "search",
        "location_id", "is_public", "ignore_DST", "coordinate_uncertainty", "date_created", "managers",
        "research_projects_member",
        "in_bbox",  # v2 only: v1's list ignores it
    })
    known_filters = {
        "v2": _V2_FILTERS,
        # v1 adds the map and the address fields (v2 has neither), and has no in_bbox on the list
        "v1": (_V2_FILTERS - {"in_bbox"}) | {"locations_map", "country", "state", "county", "city"},
    }
    export_endpoint = "/geomap/api/locations/export/"
    schema = Location
    export_schema = LocationExport

    def in_area(
        self,
        bbox: tuple[float, float, float, float] | None = None,
        center: tuple[float, float] | None = None,
        radius: float | None = None,
        **filters: Any,
    ) -> Iterator[Location]:
        """Iterate over the locations inside an area, filtering on the client.

        Trapper's location list has no usable spatial filter: Trapper v1 **ignores** ``in_bbox`` and
        ``radius`` silently and returns every location, and v2 applies ``in_bbox`` but ignores ``radius``.
        So this fetches the locations that match ``filters`` and keeps those whose coordinates fall in the
        area (see :attr:`Location.longitude`). On v2 a box that does not cross the antimeridian is also
        sent to the server as ``in_bbox``, so that fewer pages are read; on v1 it reads every page: on a big
        server, narrow it down with ``filters`` such as ``research_project``. A location whose coordinates
        cannot be read is left out.

        Give a bounding box, a circle, or both (a location must then be inside both).

        Args:
            bbox: ``(min_lon, min_lat, max_lon, max_lat)``, edges included. ``min_lon > max_lon`` crosses
                the antimeridian.
            center: ``(longitude, latitude)`` of the circle, longitude first, like Trapper.
            radius: Radius of the circle in **metres**; needs ``center``.
            **filters: Any filter of :meth:`where` (``research_project``, ``owner``, ``search``, ...).

        Raises:
            ValueError: if no area is given, if ``center`` and ``radius`` are not given together, or if
                a coordinate is out of range or ``radius`` is negative.

        Example:
            ``client.locations.in_area(center=(-6.44, 37.05), radius=5000, research_project=3)``
        """
        if bbox is None and center is None and radius is None:
            raise ValueError("give an area: bbox, or center and radius")
        if (center is None) != (radius is None):
            raise ValueError("center and radius go together")
        if bbox is not None:
            if len(bbox) != 4:
                raise ValueError("bbox is (min_lon, min_lat, max_lon, max_lat)")
            min_lon, min_lat, max_lon, max_lat = bbox
            if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180
                    and -90 <= min_lat <= 90 and -90 <= max_lat <= 90):
                raise ValueError("bbox out of range: longitude within ±180 and latitude within ±90")
            if min_lat > max_lat:
                raise ValueError("bbox: min_lat is greater than max_lat")
        if center is not None:
            if len(center) != 2 or not (-180 <= center[0] <= 180 and -90 <= center[1] <= 90):
                raise ValueError("center is (longitude, latitude), within ±180 and ±90")
            if radius < 0:
                raise ValueError("radius cannot be negative")

        def inside(loc: Location) -> bool:
            lon, lat = loc.longitude, loc.latitude
            if lon is None or lat is None:
                return False
            if bbox is not None and not in_bbox(lon, lat, bbox):
                return False
            if center is not None and distance_m(center[0], center[1], lon, lat) > radius:
                return False
            return True

        if (
            bbox is not None
            and bbox[0] <= bbox[2]
            and "in_bbox" not in filters
            and self.client.server_version == "v2"
        ):
            filters["in_bbox"] = ",".join(repr(float(v)) for v in bbox)
        return iter(self.where(filter_fn=inside, **filters))

    import_endpoint = "geomap/location/import/"
    #: Trapper v2 moved the import forms into the Django admin.
    import_endpoint_v2 = "admin/geomap/location/import-locations/"

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

        On Trapper v2 the form is the import action of the Django admin
        (``admin/geomap/location/import-locations/``); the same arguments apply. The account must be a
        staff user with the add permission, and the server imports
        asynchronously, so ``True`` means the table was validated and queued.

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
                return self._import_post(data, files)

            response = retrying(_do_request)

        if self._import_accepted(response):
            return True

        if raise_on_error:
            raise self._import_error("Location", response)
        return False

    def wait_for_import(
        self,
        location_ids: Iterable[str],
        timeout: float = 60.0,
        interval: float = 2.0,
        raise_on_timeout: bool = True,
    ) -> bool:
        """Wait until the imported locations are visible through the API.

        Trapper v2 imports asynchronously: ``import_locations()`` returning ``True`` only means the table was
        validated and queued. Neither version offers an API to query the import task, so this
        checks the outcome instead: it polls the list endpoint until every ID is there.

        Args:
            location_ids: The location IDs the import should create (the ``locationID`` column).
            timeout: Seconds to wait in total.
            interval: Seconds between polls.
            raise_on_timeout: Raise ``TimeoutError`` instead of returning ``False``.

        Returns:
            ``True`` once all of them exist; ``False`` on timeout when ``raise_on_timeout=False``.

        Raises:
            TimeoutError: Some IDs were still missing after ``timeout`` seconds.

        Example::

            client.locations.import_locations(file="locations.csv", research_project=1, timezone="Europe/Madrid")
            client.locations.wait_for_import(["don-01"])
        """
        return self._wait_for_ids(location_ids, "location_id", timeout, interval, raise_on_timeout, "location ID")
