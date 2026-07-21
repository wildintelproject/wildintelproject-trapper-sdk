import csv
import html
import io
import json
import re
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

    Attributes:
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
        self._web_csrf_token: str | None = None

    def make_request(
        self,
        endpoint: str,
        method: Literal["GET", "POST", "PATCH", "DELETE", "PUT"],
        query: Dict[str, Any] | None = None,
        body: Dict[str, Any] | None = None,
        raise_on_error: bool = True,
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
        **kwargs: Any,
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
            **kwargs: Any,
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
            **kwargs: Any,
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
        **kwargs: Any,
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
        **kwargs: Any,
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

    def post_multipart(
        self,
        endpoint: str,
        data: Dict[str, Any] | None = None,
        files: Dict[str, Any] | None = None,
        query: Dict[str, Any] | None = None,
        raise_on_error: bool = True,
    ) -> httpx.Response:
        """Perform a ``multipart/form-data`` ``POST`` request (e.g. file uploads).

        Unlike :meth:`post`, the body is not sent as JSON: ``data`` supplies
        the regular form fields and ``files`` the file part(s), matching what
        ``httpx.Client.request(data=..., files=...)`` expects.

        Args:
            endpoint: API endpoint relative to ``base_url``.
            data: Form fields to send alongside the file(s).
            files: Mapping compatible with httpx's ``files`` parameter, e.g.
                ``{"file": (filename, file_obj, content_type)}``.
            query: Query parameters.
            raise_on_error: Whether to raise mapped API exceptions.

        Returns:
            Raw ``httpx.Response``.
        """
        headers, auth = self._auth()
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            url = endpoint
        else:
            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        self.logger.debug(f"POST(multipart) {url}")
        self.logger.debug(f"Query: {query}")

        response = self._client.request(
            method="POST",
            url=url,
            headers=headers,
            auth=auth,
            params=query,
            data=data,
            files=files,
        )

        if 200 <= response.status_code < 300:
            return response
        return self._handle_error(response, raise_on_error)

    # ── cookie/session auth (for classic, non-REST Django views) ──────────────

    _CSRF_INPUT_RE = re.compile(
        r'name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)["\']'
    )

    def _csrf_token_from_html(self, html_text: str) -> str | None:
        """Scrape the CSRF token from a rendered Django form's hidden input.

        Fallback for servers where the token isn't (also) exposed as a
        ``csrftoken`` cookie — e.g. ``CSRF_USE_SESSIONS=True`` deployments,
        or a cookie dropped somewhere between us and Django (reverse proxy,
        an unfollowed redirect, ...).

        Args:
            html_text: Raw HTML body of a page containing ``{% csrf_token %}``.

        Returns:
            The token value if found, otherwise ``None``.
        """
        match = self._CSRF_INPUT_RE.search(html_text)
        return match.group(1) if match else None

    _ERROR_BLOCK_RE = re.compile(
        r'class="[^"]*\b(?:alert-danger|errorlist|invalid-feedback)\b[^"]*"[^>]*>(.*?)</(?:div|ul|p|span)>',
        re.IGNORECASE | re.DOTALL,
    )
    _TAG_RE = re.compile(r"<[^>]+>")
    _FRICTIONLESS_REPORT_RE = re.compile(r"const\s+report\s*=\s*(\{.*?\});", re.DOTALL)

    def _extract_frictionless_errors(
        self, html_text: str, max_errors: int = 20
    ) -> list[str] | None:
        """Extract per-row/per-field validation messages from an embedded frictionless report.

        ``common/table_errors.html`` (rendered on CSV/table import failures —
        e.g. :meth:`~trapper_client.components.locations.LocationsComponent.import_locations`,
        :meth:`~trapper_client.components.deployments.DeploymentsComponent.import_deployments`)
        embeds the *full* validation report as a ``const report = {...};`` JSON
        blob inside a ``<script type="module">``, meant to be rendered by a JS
        widget (``frictionless-components``) — it never appears as plain HTML
        text, so :meth:`_extract_html_error_text`'s tag-based extraction only
        ever sees the generic "your table could not be imported" banner above
        it, not the actual per-row reasons. This parses that JSON directly
        instead.

        Args:
            html_text: Raw HTML response body.
            max_errors: Maximum number of individual error messages to return.

        Returns:
            One message per validation error (row/column-level detail, e.g. a
            blacklist collision with an existing ``locationID``, a missing
            required value, ...), capped at ``max_errors``. ``None`` if no
            parseable report was found (the page may not be a table-import
            failure at all, or the server's template may have changed).
        """
        match = self._FRICTIONLESS_REPORT_RE.search(html_text)
        if not match:
            return None
        try:
            report = json.loads(match.group(1))
        except json.JSONDecodeError:
            return None

        errors: list[Any] = list(report.get("errors", []))
        for task in report.get("tasks", []):
            errors.extend(task.get("errors", []))
        if not errors:
            return None

        messages = []
        for error in errors[:max_errors]:
            if isinstance(error, str):
                messages.append(error)
            elif isinstance(error, dict):
                messages.append(
                    error.get("message") or error.get("note") or error.get("type") or str(error)
                )
            else:
                messages.append(str(error))

        if len(errors) > max_errors:
            messages.append(f"(+{len(errors) - max_errors} more errors, truncated)")
        return messages

    def _extract_html_error_text(self, html_text: str, max_len: int = 2000) -> str:
        """Best-effort extraction of a human-readable error from a Django page.

        Session-based views (see :meth:`session_post_multipart`) return full
        HTML pages on failure, not structured JSON. This tries, in order:

        1. :meth:`_extract_frictionless_errors` — the specific per-row/per-field
           validation errors, when the page is a table-import failure.
        2. Common Bootstrap/Django error markup (``alert-danger``, ``errorlist``,
           ``invalid-feedback``) — e.g. a form's ``clean()``/field validation
           errors — stripped and deduplicated.
        3. A plain-text snippet of the whole ``<body>``, if neither of the above
           found anything (the page structure may differ from what's handled here).

        Args:
            html_text: Raw HTML response body.
            max_len: Maximum length of the returned string.

        Returns:
            A short, human-readable error string.
        """
        frictionless_errors = self._extract_frictionless_errors(html_text)
        if frictionless_errors:
            return "; ".join(frictionless_errors)[:max_len]

        blocks = self._ERROR_BLOCK_RE.findall(html_text)
        if blocks:
            texts = [" ".join(html.unescape(self._TAG_RE.sub(" ", b)).split()) for b in blocks]
            texts = [t for t in texts if t]
            if texts:
                return " | ".join(dict.fromkeys(texts))[:max_len]

        body_match = re.search(r"<body[^>]*>(.*)</body>", html_text, re.IGNORECASE | re.DOTALL)
        body = body_match.group(1) if body_match else html_text
        text = " ".join(html.unescape(self._TAG_RE.sub(" ", body)).split())
        return text[:max_len]

    def _csrf_cookie_value(self) -> str:
        """Read the current CSRF token: from the cookie jar, or the cached
        value scraped from HTML during :meth:`session_login` as a fallback.

        Returns:
            The CSRF token value.

        Raises:
            err.APIError: If no token is available from either source yet —
                call :meth:`session_login` first.
        """
        token = self._client.cookies.get("csrftoken") or self._web_csrf_token
        if not token:
            raise err.APIError(
                "No CSRF token available (no csrftoken cookie, and none scraped "
                "from HTML yet) — call session_login() first"
            )
        return token

    def session_login(self, force: bool = False) -> None:
        """Authenticate a cookie-based web session (django-allauth login form).

        Some Trapper features (e.g. the CSV/GPX bulk-import view under
        ``geomap/location/import/``) are plain server-rendered HTML views
        protected by ``LoginRequiredMixin``, not part of the token-authenticated
        REST API. This performs the same GET (fetch CSRF cookie) → POST (submit
        credentials) dance a browser does against django-allauth's login form,
        storing the resulting ``sessionid`` cookie on this client's shared
        ``httpx.Client`` for subsequent calls.

        Warning:
            Unlike the rest of this SDK — which targets a stable, versioned
            REST API — this simulates an unversioned, server-rendered HTML
            login form. It has no API contract behind it: a Trapper change to
            the login page (field names, extra required fields, added 2FA/
            CAPTCHA, a different auth flow) can break this silently, with no
            deprecation notice. It follows redirects on the initial GET and
            falls back to scraping the CSRF token from the rendered HTML when
            no ``csrftoken`` cookie comes back (covers reverse proxies,
            http->https bounces, and ``CSRF_USE_SESSIONS=True`` deployments)
            — but that's still a workaround, not a guarantee: verify it
            against your actual Trapper instance before relying on it, and
            expect to need small fixes if the server's login flow differs
            further from what's handled here.

        Idempotent: does nothing if a session cookie is already present, unless
        ``force=True``.

        Note: this server has ``ACCOUNT_LOGIN_METHODS = {"email"}`` configured,
        so ``user_name`` must be the account's email address — a plain
        username will not authenticate here even if it works for the REST API.

        Args:
            force: Re-authenticate even if a session cookie is already present.

        Raises:
            ValueError: If ``user_name``/``user_password`` are not configured
                (an access token alone cannot authenticate this HTML login form).
            err.APIError: If the login attempt does not result in an
                authenticated session (wrong credentials, changed login form, ...).
        """
        if not force and self._client.cookies.get("sessionid"):
            return

        if not (self.user_name and self.user_password):
            raise ValueError(
                "session_login() requires user_name/user_password — an access_token "
                "alone cannot authenticate the web login form"
            )

        login_url = f"{self.base_url.rstrip('/')}/account/login/"
        # follow_redirects=True here: some deployments redirect this GET
        # (http->https, a reverse proxy, a trailing-slash/`next=` bounce, ...)
        # before rendering the actual login form — and only the *rendered*
        # response sets the CSRF cookie / embeds the csrfmiddlewaretoken
        # input. The login POST below deliberately does NOT follow redirects,
        # since a 302 there is how we detect a successful login.
        login_page = self._client.get(login_url, follow_redirects=True)
        csrf_token = self._client.cookies.get("csrftoken") or self._csrf_token_from_html(login_page.text)

        if not csrf_token:
            raise err.APIError(
                f"Could not find a CSRF token at {login_page.url} (status "
                f"{login_page.status_code}) — no csrftoken cookie and none embedded "
                "in the page's HTML. The login form may have a different structure "
                "on this server; inspect that URL in a browser to compare."
            )
        self._web_csrf_token = csrf_token

        response = self._client.post(
            str(login_page.url),
            data={
                "login": self.user_name,
                "password": self.user_password,
                "csrfmiddlewaretoken": csrf_token,
            },
            headers={"Referer": str(login_page.url)},
        )

        if response.status_code != 302 or not self._client.cookies.get("sessionid"):
            raise err.APIError(
                f"Web session login failed (status {response.status_code} from "
                f"{response.url}) — check user_name/user_password (user_name must "
                "be the account email on this server), or inspect the response body "
                "for a rendered error message."
            )

    def session_post_multipart(
        self,
        endpoint: str,
        data: Dict[str, Any] | None = None,
        files: Dict[str, Any] | None = None,
    ) -> httpx.Response:
        """POST multipart/form-data to a classic (non-REST) Django view.

        Authenticates a cookie-based web session first (see
        :meth:`session_login`), since these views rely on Django's
        session/CSRF machinery instead of the API's token auth. Unlike
        :meth:`post_multipart`, the response is *not* JSON: these are
        server-rendered HTML views, so the caller must interpret the raw
        ``httpx.Response`` itself — typically a ``302`` redirect means
        success, while a ``200`` re-renders the form (or an error page) with
        validation errors embedded in the HTML.

        Warning:
            Same caveat as :meth:`session_login`: this targets an unversioned
            HTML view, not a documented API contract, and has not been
            validated against a live Trapper server. Treat it as a
            best-effort workaround, not a stable integration point.

        Args:
            endpoint: Endpoint relative to ``base_url``.
            data: Form fields, excluding ``csrfmiddlewaretoken`` (added automatically).
            files: Mapping compatible with httpx's ``files`` parameter.

        Returns:
            Raw ``httpx.Response`` (redirects are not followed).
        """
        self.session_login()
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        form_data = dict(data or {})
        form_data["csrfmiddlewaretoken"] = self._csrf_cookie_value()
        return self._client.post(url, data=form_data, files=files, headers={"Referer": url})

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
            endpoint: API endpoint relative to ``base_url``, or an already
                absolute URL (``http://`` / ``https://``) — used as-is
                without joining it to ``base_url``. Some Trapper responses
                (e.g. media ``filePath``) already return absolute download
                URLs with an access token embedded in the query string.
            method: HTTP method string.
            query: Query parameters.
            body: JSON request body.

        Returns:
            Raw ``httpx.Response``.
        """
        headers, auth = self._auth()
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            url = endpoint
        else:
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
