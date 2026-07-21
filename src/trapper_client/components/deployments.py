"""
Component for the /api/deployments/ resource.
"""

from __future__ import annotations

import time
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Dict

from tenacity import Retrying

from trapper_client import err
from trapper_client.api_query import APIQuery
from trapper_client.components.base import TrapperComponent
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
    - ``collections`` (int or list): Filter by collection ID(s) (via ``colls`` param)
    - ``correct_setup`` (bool): Filter by setup correctness
    - ``correct_tstamp`` (bool): Filter by timestamp correctness
    - ``search`` (str): Search in deployment_id or owner__username

    **Examples:**

        # All deployments in collection 5
        for dep in client.deployments.where(collections=5):
            print(dep)

        # Shortcut: deployments by collection
        for dep in client.deployments.by_collection(5):
            print(dep)

        # Filter by location and date range
        for dep in client.deployments.where(location=42, sdate_from="2024-01-01"):
            print(dep)

        # Export to CSV
        client.deployments.export_by_collection(5, file="/tmp/deps.csv")

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
                return self.client.session_post_multipart(
                    self.import_endpoint, data=data, files=files,
                )

            response = retrying(_do_request)

        if response.status_code == 302:
            return True

        if raise_on_error:
            message = self.client._extract_html_error_text(response.text)
            raise err.APIError(
                f"Deployment import failed (status {response.status_code}): {message}"
            )
        return False

    def by_collection(
        self,
        collection_id: int,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        **kwargs: Any,
    ) -> APIQuery[Deployment]:
        """Return a lazy iterator over deployments filtered by collection.

        Args:
            collection_id: Collection primary key (mapped to ``colls`` param).
            query: Base query parameters.
            page_size: Number of items requested per API page.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Lazy ``APIQuery`` iterator yielding deployments.
        """
        q = dict(query or {})
        q["colls"] = collection_id
        return self.where(query=q, page_size=page_size, **kwargs)

    def export_by_collection(
        self,
        collection_id: int,
        query: Dict[str, Any] | None = None,
        file: str | Path | None = None,
        **kwargs: Any,
    ) -> Path | list[DeploymentExport]:
        """Export deployments of a collection to CSV.

        Args:
            collection_id: Collection primary key (mapped to ``colls`` param).
            query: Base query parameters.
            file: Output CSV file path. If ``None``, returns a list of models.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            ``Path`` to the generated CSV when ``file`` is provided,
            otherwise ``list[DeploymentExport]``.
        """
        q = dict(query or {})
        q["colls"] = collection_id
        return self.export(query=q, file=file, **kwargs)
