import csv
import io
import tempfile
import zipfile

from pathlib import Path
from typing import Dict, Any
import httpx
import attr
from typing_extensions import Literal
from trapper_client import err
import logging
import gzip
import bz2

logger = logging.getLogger(__name__)


@attr.s
class APIClientBase:
    """
    Base client for interacting with the Trapper API.

    Provides authentication, HTTP request handling, pagination, and processing of
    JSON or CSV responses (including CSV inside ZIP, gzip, or bzip2). CSV responses
    can be optionally normalized to JSON with pagination.

    Args:
        access_token: Authentication token used for API requests.
        user_name: Username for basic authentication.
        user_password: Password for basic authentication.
        verify_ssl: Whether to verify SSL certificates.
        base_url: Base URL of the Trapper API.
        timeout: Request timeout in seconds.
    """

    access_token: str = attr.ib(repr=False, default=None)
    user_name: str = attr.ib(repr=False, default=None)
    user_password: str = attr.ib(repr=False, default=None)
    verify_ssl: bool = attr.ib(repr=False, default=True)
    base_url: str = attr.ib(repr=False, default="https://trapper_api_client-trap.uhu.es")
    logger = attr.ib(repr=False, default=logger)
    timeout: int = attr.ib(default=30)
    _client: httpx.Client = attr.ib(init=False, repr=False)
    name = "trapper_api_client"
    user_id: str = "me"

    def __attrs_post_init__(self):
        """Validate authentication configuration after attrs initialization.

        Returns:
            ``None``.

        Raises:
            ValueError: If neither token nor user/password are configured.
        """
        if not self.access_token and not (self.user_name and self.user_password):
            raise ValueError("Token or user/password must be provided for authentication")
        self._client = httpx.Client(verify=self.verify_ssl, timeout=self.timeout)

    def make_request(
        self,
        endpoint: str,
        method: Literal["GET", "POST", "PATCH", "DELETE", "PUT"],
        query: Dict[str, Any] | None = None,
        body: Dict[str, Any] | None = None,
        raise_on_error=True,
    ) -> httpx.Response:
        """Send one HTTP request to the Trapper API.

        Args:
            endpoint: API endpoint relative to ``base_url``.
            method: HTTP method.
            query: Query parameters.
            body: JSON request body.
            raise_on_error: Whether to raise mapped API exceptions.

        Returns:
            Raw ``httpx.Response`` object.
        """
        self._validate_method(method)
        r = self._send_request(endpoint=endpoint, method=method, query=query, body=body)

        if 200 <= r.status_code < 300:
            return r

        return self._handle_error(r, raise_on_error)

    def get(
        self,
        endpoint: str,
        query: Dict[str, Any] | None = None,
        raise_on_error: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """Perform a ``GET`` request and normalize response payload.

        Args:
            endpoint: API endpoint relative to ``base_url``.
            query: Base query parameters.
            raise_on_error: Whether to raise mapped API exceptions.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Normalized response as dictionary with pagination/results envelope.
        """
        query = self._merge_query_params(query, kwargs)
        response = self.make_request(endpoint, method="GET", query=query, raise_on_error=raise_on_error)
        return self._handle_success(response)

    def get_one(
            self,
            endpoint: str,
            query: Dict[str, Any] | None = None,
            raise_on_error: bool = True,
            **kwargs,
    ) -> Dict[str, Any]:
        """Perform a ``GET`` request and return the raw response dict without pagination wrapping.

        Use this for detail endpoints that return a single object directly,
        not a paginated list.

        Args:
            endpoint: API endpoint relative to ``base_url``.
            query: Base query parameters.
            raise_on_error: Whether to raise mapped API exceptions.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Raw response dictionary as returned by the API.
        """
        query = self._merge_query_params(query, kwargs)
        response = self.make_request(endpoint, method="GET", query=query, raise_on_error=raise_on_error)
        return response.json()

    def find(
            self,
            endpoint: str,
            query: Dict[str, Any] | None = None,
            raise_on_error: bool = True,
            **kwargs,
    ) -> Dict[str, Any]:
        """ get_one alias"""

        return self.get_one(
            endpoint,
            query,
            raise_on_error,
            **kwargs,
        )

    def export(
        self,
        endpoint: str,
        query: Dict[str, Any] | None = None,
        raise_on_error: bool = True,
        file: str | Path | None = None,
        **kwargs,
    ) -> Path | list[dict]:
        """Export one response page to CSV or return raw results as a list.

        If ``file`` is provided, the response is written to a CSV file and the
        path is returned. If ``file`` is ``None`` and the response is JSON,
        the raw ``results`` list is returned directly without writing any file.

        Note: When the response is a direct CSV stream (not JSON), a file is
        always written even if ``file`` is ``None``, because the content cannot
        be meaningfully returned as a list of dicts without parsing.

        Args:
            endpoint: API endpoint relative to ``base_url``.
            query: Base query parameters.
            raise_on_error: Whether to raise mapped API exceptions.
            file: Output CSV file path. If ``None`` and response is JSON,
                returns the raw results list instead of writing a file.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            ``list[dict]`` with raw result rows when ``file`` is ``None`` and
            the response is JSON; otherwise ``Path`` to the generated CSV file.
        """
        query = self._merge_query_params(query, kwargs)
        response = self.make_request(endpoint, method="GET", query=query, raise_on_error=raise_on_error)

        if self.is_json(response):
            data = self._handle_json_response(response)
            rows = data.get("results", [])
            if file is None:
                return rows
            output_path = self._select_file(file)
            self._write_csv(rows, output_path)
            return output_path

        # si es CSV directo
        csv_text = self._extract_csv_text(response)
        if file is None:
            reader = csv.DictReader(io.StringIO(csv_text))
            return list(reader)

        output_path = self._select_file(file)
        output_path.write_text(csv_text, encoding="utf-8")

        return output_path

    def get_all(
        self,
        endpoint: str,
        query: Dict[str, Any] | None = None,
        raise_on_error: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """Fetch and merge all pages from an endpoint.

        Args:
            endpoint: API endpoint relative to ``base_url``.
            query: Base query parameters.
            raise_on_error: Whether to raise mapped API exceptions.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            Dictionary with merged ``results`` and final ``pagination``.
        """
        query = self._merge_query_params(query, kwargs)
        return self.get_all_pages(endpoint, query=query, raise_on_error=raise_on_error)

    def get_all_pages(
        self,
        endpoint: str,
        query: Dict[str, Any] | None = None,
        raise_on_error: bool = True,
    ) -> Dict[str, Any]:
        """Retrieve all paginated results from an endpoint.

        Args:
            endpoint: API endpoint relative to ``base_url``.
            query: Base query parameters.
            raise_on_error: Whether to raise mapped API exceptions.

        Returns:
            Dictionary with merged ``results`` and final ``pagination``.
        """
        query = {} if query is None else query.copy()
        query.pop("page", None)

        data = self.get(endpoint, query=query, raise_on_error=raise_on_error)
        pagination = data.get("pagination", {"page": 1, "pages": 1})
        page = pagination.get("page", 1)
        pages = pagination.get("pages", 1)

        results = {k: (v[:] if isinstance(v, list) else v) for k, v in data.items()}

        while page < pages:
            page += 1
            query["page"] = page
            next_page = self.get(endpoint, query=query, raise_on_error=raise_on_error)

            for k, v in next_page.items():
                if isinstance(v, list) and k in results:
                    results[k].extend(v)
                elif k not in results:
                    results[k] = v

            pagination = next_page.get("pagination", pagination)

        results["pagination"] = pagination
        return results

    def export_all(
        self,
        endpoint: str,
        query: Dict[str, Any] | None = None,
        raise_on_error: bool = True,
        file: str | Path | None = None,
    ) -> Path:
        """Retrieve all pages from endpoint and save as CSV.

        Args:
            endpoint: API endpoint relative to ``base_url``.
            query: Base query parameters.
            raise_on_error: Whether to raise mapped API exceptions.
            file: Output CSV file path.

        Returns:
            Path to generated CSV file.
        """
        response = self.make_request(endpoint, method="GET", query=query, raise_on_error=raise_on_error)
        output_path = self._select_file(file)

        if self.is_json(response):
            data = self._handle_json_response(response)
            rows = data.get("results", [])

            pagination = data.get("pagination", {"page": 1, "pages": 1})
            page = pagination.get("page", 1)
            pages = pagination.get("pages", 1)

            query = {} if query is None else query.copy()
            while page < pages:
                page += 1
                query["page"] = page
                next_resp = self.make_request(endpoint, method="GET", query=query, raise_on_error=raise_on_error)
                next_data = self._handle_json_response(next_resp)
                rows.extend(next_data.get("results", []))

            self._write_csv(rows, output_path)
            return output_path

        csv_text = self._extract_csv_text(response)
        output_path.write_text(csv_text, encoding="utf-8")
        return output_path

    def post(
        self,
        endpoint: str,
        query: Dict[str, Any] | None = None,
        body: Dict[str, Any] | None = None,
        raise_on_error: bool = True,
    ) -> httpx.Response:
        """Perform a ``POST`` request.

        Args:
            endpoint: API endpoint relative to ``base_url``.
            query: Query parameters.
            body: JSON request body.
            raise_on_error: Whether to raise mapped API exceptions.

        Returns:
            Raw ``httpx.Response``.
        """
        return self.make_request(endpoint, method="POST", query=query, body=body, raise_on_error=raise_on_error)

    def patch(
        self,
        endpoint: str,
        query: Dict[str, Any] | None = None,
        body: Dict[str, Any] | None = None,
        raise_on_error: bool = True,
    ) -> httpx.Response:
        """Perform a ``PATCH`` request.

        Args:
            endpoint: API endpoint relative to ``base_url``.
            query: Query parameters.
            body: JSON request body.
            raise_on_error: Whether to raise mapped API exceptions.

        Returns:
            Raw ``httpx.Response``.
        """
        return self.make_request(endpoint, method="PATCH", query=query, body=body, raise_on_error=raise_on_error)

    def put(
        self,
        endpoint: str,
        query: Dict[str, Any] | None = None,
        body: Dict[str, Any] | None = None,
        raise_on_error: bool = True,
    ) -> httpx.Response:
        """Perform a ``PUT`` request.

        Args:
            endpoint: API endpoint relative to ``base_url``.
            query: Query parameters.
            body: JSON request body.
            raise_on_error: Whether to raise mapped API exceptions.

        Returns:
            Raw ``httpx.Response``.
        """
        return self.make_request(endpoint, method="PUT", query=query, body=body, raise_on_error=raise_on_error)

    def delete(
        self,
        endpoint: str,
        query: Dict[str, Any] | None = None,
        body: Dict[str, Any] | None = None,
        raise_on_error: bool = True,
    ) -> httpx.Response:
        """Perform a ``DELETE`` request.

        Args:
            endpoint: API endpoint relative to ``base_url``.
            query: Query parameters.
            body: Optional JSON request body.
            raise_on_error: Whether to raise mapped API exceptions.

        Returns:
            Raw ``httpx.Response``.
        """
        return self.make_request(endpoint, method="DELETE", query=query, body=body, raise_on_error=raise_on_error)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _paginate(self, items, page: int, per_page: int = 10):
        """Return a local page slice from a sequence.

        Args:
            items: Sequence-like object.
            page: One-based page number.
            per_page: Items per page.

        Returns:
            Page slice.
        """
        start = (page - 1) * per_page
        end = start + per_page
        return items[start:end]

    def _auth(self):
        """Build authentication headers/auth tuple for requests.

        Returns:
            Tuple ``(headers, auth)`` compatible with ``requests``.

        Raises:
            ValueError: If no authentication method is configured.
        """
        if self.access_token:
            return {"Authorization": f"Token {self.access_token}"}, None
        elif self.user_name and self.user_password:
            return {}, (self.user_name, self.user_password)
        else:
            raise ValueError("No se ha configurado ni token ni usuario/clave")

    def _validate_method(self, method: str):
        """Validate that HTTP method is supported.

        Args:
            method: HTTP method string.

        Returns:
            ``None``.

        Raises:
            ValueError: If method is not supported.
        """
        allowed = {"GET", "POST", "PATCH", "DELETE", "PUT"}
        if method not in allowed:
            raise ValueError(f"Invalid method: {method}")

    def _send_request(
        self,
        endpoint: str,
        method: str,
        query: Dict[str, Any] | None,
        body: Dict[str, Any] | None,
    ) -> httpx.Response:
        """Send low-level HTTP request using the configured session.

        Args:
            endpoint: API endpoint relative to ``base_url``.
            method: HTTP method string.
            query: Query parameters.
            body: JSON request body.

        Returns:
            Raw ``httpx.Response``.
        """
        headers, auth = self._auth()
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        self.logger.debug(f"{method} {url}")
        self.logger.debug(f"Query: {query}")
        self.logger.debug(f"Body: {body}")

        return self._client.request(
            method=method,
            url=url,
            headers=headers,
            auth=auth,
            params=query,
            json=body,
        )

    def _select_file(self, file: str | Path | None) -> Path:
        """Resolve output file path and ensure parent directory exists.

        Args:
            file: Desired output path or ``None`` for temporary file.

        Returns:
            Resolved writable file path.
        """
        if file is None:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
            output_path = Path(tmp.name)
            tmp.close()
        else:
            output_path = Path(file)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    def is_csv(self, response: httpx.Response) -> bool:
        """Check whether response contains CSV payload.

        Args:
            response: HTTP response object.

        Returns:
            ``True`` when response looks like CSV; otherwise ``False``.
        """
        content_type = response.headers.get("Content-Type", "").lower()
        return "text/csv" in content_type

    def is_zip(self, response: httpx.Response) -> bool:
        """Check whether response contains ZIP payload.

        Args:
            response: HTTP response object.

        Returns:
            ``True`` when response looks like ZIP; otherwise ``False``.
        """
        content_type = response.headers.get("Content-Type", "").lower()
        return "application/zip" in content_type or response.content[:4] == b"PK\x03\x04"

    def is_gzip(self, response: httpx.Response) -> bool:
        """Check whether response contains gzip payload.

        Args:
            response: HTTP response object.

        Returns:
            ``True`` when response looks like gzip; otherwise ``False``.
        """
        content_type = response.headers.get("Content-Type", "").lower()
        return "gzip" in content_type or response.content[:2] == b"\x1f\x8b"

    def is_bzip2(self, response: httpx.Response) -> bool:
        """Check whether response contains bzip2 payload.

        Args:
            response: HTTP response object.

        Returns:
            ``True`` when response looks like bzip2; otherwise ``False``.
        """
        content_type = response.headers.get("Content-Type", "").lower()
        return "bzip2" in content_type or response.content[:2] == b"BZ"

    def is_json(self, response: httpx.Response) -> bool:
        """Check whether response contains JSON payload.

        Args:
            response: HTTP response object.

        Returns:
            ``True`` when content type is JSON; otherwise ``False``.
        """
        content_type = response.headers.get("Content-Type", "").lower()
        return "application/json" in content_type

    def _handle_success(self, response: httpx.Response) -> Dict[str, Any]:
        """Normalize successful response into a common dictionary structure.

        Args:
            response: HTTP response object.

        Returns:
            Dictionary containing parsed data with pagination/results envelope.

        Raises:
            ValueError: If response content type is unsupported.
        """
        content_type = response.headers.get("Content-Type", "").lower()

        if "application/json" in content_type:
            return self._handle_json_response(response)

        if self.is_csv(response) or self.is_zip(response) or self.is_gzip(response) or self.is_bzip2(response):
            return self._handle_csv_response(response)

        self.logger.warning(f"Received response with unsupported content type: {content_type}")
        raise ValueError(f"Unsupported content type: {content_type}")

    def _handle_json_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Normalize JSON response into pagination/results envelope.

        Args:
            response: HTTP response object.

        Returns:
            Dictionary with ``pagination`` and ``results`` keys.
        """
        data = response.json()

        if isinstance(data, dict) and "pagination" in data and "results" in data:
            return data

        rows = data if isinstance(data, list) else [data]

        return {
            "pagination": {
                "page": 1,
                "page_size": len(rows),
                "pages": 1,
                "count": len(rows),
            },
            "results": rows,
        }

    def _handle_csv_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Parse CSV-like response formats into pagination/results envelope.

        Args:
            response: HTTP response object.

        Returns:
            Dictionary with parsed CSV rows under ``results``.
        """
        csv_text = self._extract_csv_text(response)
        self.logger.debug(f"Extracted CSV text (first 500 chars): {csv_text[:500]}")

        reader = csv.DictReader(io.StringIO(csv_text, newline=""))
        rows = list(reader)

        if rows:
            self.logger.debug(f"CSV response parsed into {len(rows)} rows. Sample row: {rows[0]}")

        return {
            "pagination": {
                "page": 1,
                "page_size": len(rows),
                "pages": 1,
                "count": len(rows),
            },
            "results": rows,
        }

    def _write_csv(self, rows: list[dict], path: Path) -> None:
        """Write rows to CSV file.

        Args:
            rows: List of row dictionaries.
            path: Output CSV file path.

        Returns:
            ``None``.
        """
        if not rows:
            path.write_text("", encoding="utf-8")
            return

        fieldnames = sorted({k for row in rows for k in row.keys()})
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _extract_csv_text(self, response: httpx.Response) -> str:
        """Extract CSV text from plain, ZIP, gzip or bzip2 responses.

        Args:
            response: HTTP response object.

        Returns:
            Decoded CSV text.

        Raises:
            err.APIError: If payload is unsupported or ZIP has no CSV file.
        """
        content_type = response.headers.get("Content-Type", "").lower()
        self.logger.debug(f"Extracting CSV from content type: {content_type}")

        if response.content[:2] == b"\x1f\x8b":
            self.logger.debug("Reading CSV from gzip content (detected by magic bytes)")
            return gzip.decompress(response.content).decode("utf-8")

        if self.is_csv(response):
            return response.text

        if self.is_zip(response):
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                for name in z.namelist():
                    if name.lower().endswith(".csv"):
                        with z.open(name) as f:
                            self.logger.debug(f"Reading CSV from ZIP file: {name}")
                            return f.read().decode("utf-8")
            raise err.APIError("ZIP file does not contain a CSV")

        if self.is_gzip(response):
            self.logger.debug("Reading CSV from gzip content")
            return gzip.decompress(response.content).decode("utf-8")

        if self.is_bzip2(response):
            self.logger.debug("Reading CSV from bzip2 content")
            return bz2.decompress(response.content).decode("utf-8")

        raise err.APIError(f"Unsupported CSV content type or format: {content_type}")

    def _handle_error(self, response: httpx.Response, raise_on_error: bool) -> httpx.Response:
        """Handle non-2xx responses and optionally raise mapped errors.

        Args:
            response: HTTP response object.
            raise_on_error: Whether to raise mapped API exceptions.

        Returns:
            Original response when ``raise_on_error=False``.

        Raises:
            err.APIError: Generic API error.
            Exception: Specific mapped HTTP exception from ``HTTP_ERRORS_MAP``.
        """
        try:
            body = response.json()
            message = body.get("_error", {}).get("message", body)
        except Exception:
            message = response.text

        self.logger.error(f"Request failed [{response.status_code}] {message}")

        if not raise_on_error:
            return response

        if response.status_code in err.HTTP_ERRORS_MAP:
            raise err.HTTP_ERRORS_MAP[response.status_code](message)

        raise err.APIError(message)

    def _merge_query_params(
        self,
        query: Dict[str, Any] | None,
        extra: Dict[str, Any],
    ) -> Dict[str, Any] | None:
        """Merge base query parameters with extra values.

        Args:
            query: Base query parameters.
            extra: Extra query parameters.

        Returns:
            Merged dictionary, or ``None`` when empty.
        """
        merged = dict(query or {})
        merged.update(extra)
        return merged or None
