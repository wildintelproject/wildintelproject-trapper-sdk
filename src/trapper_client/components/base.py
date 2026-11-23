"""
Base class for all Trapper API components.
"""

from __future__ import annotations

import logging
import re
import time
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Generic, Iterable, TypeVar, Union

from pydantic import BaseModel

from trapper_client import err
from trapper_client.api_query import APIQuery, parse_row
from trapper_client.schemas import PaginatedResult, Pagination

if TYPE_CHECKING:
    from trapper_client.api_client_base import APIClientBase

logger = logging.getLogger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)


def selected_option(html: str, select_name: str) -> str | None:
    """The value of the ``selected`` option of ``<select name=select_name>`` in a rendered form."""
    block = re.search(
        rf'<select[^>]*name="{re.escape(select_name)}"[^>]*>(.*?)</select>', html, re.DOTALL
    )
    if not block:
        return None
    option = re.search(r'<option[^>]*value="([^"]+)"[^>]*selected', block.group(1))
    return option.group(1) if option else None


class TrapperComponent(Generic[TModel]):
    """
    Base component for a Trapper API resource.

    Subclasses define:
    - ``endpoint``: relative API endpoint for the resource.
    - ``schema``: Pydantic model used to parse each item.

    The component provides two access patterns:
    - page-based access (``get``/``get_all``/``all``), returning ``PaginatedResult``
    - lazy iteration (``where``), returning ``APIQuery``

    It also provides single-item access via ``find`` and convenience write helpers.
    """

    endpoint: str = ""
    schema: type[TModel]
    export_schema: type[BaseModel] | None = None
    export_endpoint: str | None = None
    #: Trapper major versions the resource exists in. Narrow it (e.g. ``("v1",)``) for
    #: resources a version dropped; every read method then fails fast with
    #: :class:`~trapper_client.err.UnsupportedVersionError` instead of a bare 404.
    supported_versions: tuple[str, ...] = ("v1", "v2")

    def __init__(self, client: "APIClientBase"):
        self.client = client

    def _require_version(self, *versions: str, feature: str | None = None) -> None:
        """Raise ``UnsupportedVersionError`` unless the server runs one of ``versions``.

        Reading ``client.server_version`` may probe the server once (``trapper_version="auto"``),
        so only components or methods that really are version-specific call this.
        """
        current = self.client.server_version
        if current not in versions:
            name = feature or type(self).__name__
            raise err.UnsupportedVersionError(
                f"{name} is only available in Trapper {' / '.join(versions)}, "
                f"but this server runs Trapper {current}."
            )

    def _ensure_supported(self) -> None:
        """Version guard for the whole component; a no-op when it exists in every version."""
        if self.supported_versions != ("v1", "v2"):
            self._require_version(*self.supported_versions)

    def _import_post(self, data: Dict[str, Any], files: Dict[str, Any]) -> Any:
        """POST a CSV/GPX import form: v1's web view, or v2's Django-admin action.

        The two versions use different URLs (``import_endpoint`` / ``import_endpoint_v2``) and v2's
        admin needs the CSRF token read from the form page.
        """
        if self.client.server_version == "v2":
            return self.client.session_post_multipart(
                self.import_endpoint_v2, data=data, files=files, csrf_from_page=True
            )
        return self.client.session_post_multipart(self.import_endpoint, data=data, files=files)

    def _owner_role_fields(
        self,
        form_endpoint: str,
        prefix: str,
        label: str,
        members: Iterable[tuple[int, int]] = (),
    ) -> Dict[str, Any]:
        """The role formset a create form always posts: the logged-in user as administrator, and
        after them the ``members`` (``(user pk, role)`` pairs).

        The form page already says who the creator is (the owner is pre-selected in the first row
        of the formset ``prefix``), so read it from there instead of looking the user up through the
        API.

        Raises:
            ValueError: A member is the account that creates the project, who is already its
                administrator.
        """
        members = list(members)
        self.client.session_login()
        url = f"{self.client.base_url.rstrip('/')}/{form_endpoint.lstrip('/')}"
        page = self.client._web_client.get(url)
        if page.status_code != 200:
            raise err.APIError(
                f"Cannot open the {label} form (status {page.status_code}): the account "
                "may not be allowed to create it."
            )
        user = selected_option(page.text, f"{prefix}-0-user")
        role = selected_option(page.text, f"{prefix}-0-name")
        if user is None or role is None:
            raise err.APIError(
                f"The {label} form has no pre-selected owner role: Trapper changed the "
                "form and this workaround needs updating."
            )
        if any(str(pk) == str(user) for pk, _ in members):
            raise ValueError(
                f"user {user} is the account that creates the {label}, who is already its "
                "administrator: leave them out of the members"
            )
        fields: Dict[str, Any] = {
            f"{prefix}-TOTAL_FORMS": 1 + len(members),
            f"{prefix}-INITIAL_FORMS": 0,
            f"{prefix}-MIN_NUM_FORMS": 0,
            f"{prefix}-MAX_NUM_FORMS": 1000,
            f"{prefix}-0-id": "",
            f"{prefix}-0-user": user,
            f"{prefix}-0-name": role,
        }
        for row, (member_pk, member_role) in enumerate(members, start=1):
            fields[f"{prefix}-{row}-id"] = ""
            fields[f"{prefix}-{row}-user"] = member_pk
            fields[f"{prefix}-{row}-name"] = member_role
        return fields

    def _submit_create_form(
        self,
        form_endpoint: str,
        data: Dict[str, Any],
        label: str,
        raise_on_error: bool,
        field_prefix: str | None = None,
    ) -> Any | None:
        """POST a classic create form; return the server's response when it accepted it.

        Trapper answers ``302`` to the project list when it saves, and ``200`` with the form
        re-rendered (and the reasons in it) when it does not. A ``302`` to the login page is a
        refusal, not a success. ``field_prefix`` is the prefix of the form's fields when the page
        carries several forms, so that only its own errors are reported.
        """
        response = self.client.session_post_multipart(form_endpoint, data=data)
        if self._import_accepted(response):
            return response
        if not raise_on_error:
            return None
        if response.status_code == 302:
            raise err.APIError(
                f"{label} creation refused: the server redirected to its login page."
            )
        message = (
            field_prefix and self.client._extract_form_field_errors(response.text, field_prefix)
        ) or self.client._extract_html_error_text(response.text)
        raise err.APIError(f"{label} creation failed (status {response.status_code}): {message}")

    @staticmethod
    def _import_accepted(response: Any) -> bool:
        """Whether a classic-form import POST was accepted.

        The server answers ``302`` to the changelist on success. A ``302`` back to a login
        page means the session has no permission for the form (e.g. a non-staff user on
        Trapper v2's admin), which must not be mistaken for success.
        """
        if response.status_code != 302:
            return False
        return "login" not in (response.headers.get("location") or "").lower()

    def _import_error(self, label: str, response: Any) -> err.APIError:
        """Build the ``APIError`` for a rejected import POST, naming the real cause."""
        location = (response.headers.get("location") or "").lower()
        if response.status_code == 302 and "login" in location:
            return err.APIError(
                f"{label} import refused: the server redirected to its login page. The account "
                "is not allowed to use the import form (on Trapper v2 it needs a staff account "
                "with the add permission)."
            )
        message = self.client._extract_html_error_text(response.text)
        return err.APIError(f"{label} import failed (status {response.status_code}): {message}")

    @staticmethod
    def _unwrap_feature_collection(data: Any) -> Any:
        """Return the GeoJSON ``FeatureCollection`` from ``client.get``'s envelope.

        ``client.get`` wraps non-paginated bodies as ``{"pagination": ..., "results": [body]}``;
        anything that is not exactly that is returned unchanged.
        """
        results = data.get("results") if isinstance(data, dict) else None
        if (
            isinstance(results, list)
            and len(results) == 1
            and isinstance(results[0], dict)
            and results[0].get("type") == "FeatureCollection"
        ):
            return results[0]
        return data

    def _wait_for_ids(
        self,
        ids: Iterable[str],
        id_attr: str,
        timeout: float,
        interval: float,
        raise_on_timeout: bool,
        label: str,
    ) -> bool:
        """Poll the list API until every id in ``ids`` shows up (``search`` + exact match)."""
        pending = list(dict.fromkeys(str(i) for i in ids))
        deadline = time.monotonic() + timeout
        while True:
            pending = [
                i for i in pending
                if not any(getattr(row, id_attr, None) == i for row in self.where(search=i, page_size=20))
            ]
            if not pending:
                return True
            if time.monotonic() >= deadline:
                if raise_on_timeout:
                    raise TimeoutError(
                        f"{len(pending)} {label}(s) still missing after {timeout:g}s: {', '.join(pending[:10])}"
                    )
                return False
            time.sleep(interval)

    #: Query parameters that are never filters.
    _PAGING_PARAMS = frozenset({"page", "page_size"})

    #: The filters the list endpoint applies, by server version (``{"v1": {...}, "v2": {...}}``).
    #: Trapper ignores any other parameter without an error, so the SDK warns about it
    #: (:class:`~trapper_client.err.UnknownFilterWarning`). ``None`` means "not known": no check.
    known_filters: Dict[str, frozenset[str]] | None = None

    #: Filters that Trapper does apply but answers with an error (a ``500``), with the reason:
    #: ``{"name": "answers 500"}``. They get an :class:`~trapper_client.err.UnknownFilterWarning` too.
    broken_filters: Dict[str, str] = {}

    def _normalize_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Hook: put the values of a query in the form the server reads (see ``ResourcesComponent``)."""
        return query

    def _warn_unknown_filters(self, query: Dict[str, Any], stacklevel: int = 3) -> None:
        """Warn about the parameters of ``query`` that the server would ignore silently, or fail on."""
        broken = sorted(k for k in query if k in self.broken_filters)
        if broken:
            warnings.warn(
                f"{self.endpoint}: " + "; ".join(f"{k!r}: Trapper {self.broken_filters[k]}" for k in broken),
                err.UnknownFilterWarning,
                stacklevel=stacklevel,
            )
        if not self.known_filters:
            return
        # Not every call has to learn the server version (that is a request): only a parameter that some
        # version does not apply needs it.
        common = frozenset.intersection(*self.known_filters.values()) | self._PAGING_PARAMS | set(self.broken_filters)
        if all(k in common for k in query):
            return
        known = self.known_filters.get(self.client.server_version)
        if known is None:
            return
        unknown = sorted(
            k for k in query if k not in known and k not in self._PAGING_PARAMS and k not in self.broken_filters
        )
        if unknown:
            warnings.warn(
                f"{self.endpoint}: Trapper {self.client.server_version} ignores "
                f"{', '.join(repr(k) for k in unknown)} and returns every item; "
                f"the filters it applies are {', '.join(sorted(known))}",
                err.UnknownFilterWarning,
                stacklevel=stacklevel,
            )

    def _merge_query(self, query: Dict[str, Any] | None, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Merge ``query`` and ``kwargs`` into one query-params dictionary.

        Args:
            query: Base query parameters.
            kwargs: Extra query parameters.

        Returns:
            Merged dictionary, or ``None`` when no params are present.
        """
        q = dict(query or {})
        q.update(kwargs)
        q = self._normalize_query(q)
        self._warn_unknown_filters(q, stacklevel=4)
        return q

    def _to_model(self, row: Any, validate: bool, schema: type[TModel] | None = None) -> TModel:
        """
        Convert one raw row into the configured schema type.

        Args:
            row: Raw row payload from API.
            validate: Whether to run full Pydantic validation.
            schema: Schema to use for parsing. Defaults to ``self.schema``.

        Returns:
            Parsed model instance.
        """
        return parse_row(row, schema or self.schema, validate)

    def _to_paginated(self, data: Dict[str, Any], validate: bool, schema: type[TModel] | None = None) -> PaginatedResult[TModel]:
        """
        Convert an API payload into ``PaginatedResult[TModel]``.

        Missing pagination fields are filled with sensible defaults.

        Args:
            data: API payload containing ``results`` and optional ``pagination``.
            validate: Whether to validate each row with Pydantic.
            schema: Schema to use for parsing rows. Defaults to ``self.schema``.

        Returns:
            ``PaginatedResult[TModel]`` with typed rows and normalized pagination.
        """
        rows = data.get("results", [])
        items = [self._to_model(row, validate=validate, schema=schema) for row in rows]

        raw_pagination = data.get("pagination", {})
        pagination = Pagination.model_validate(
            {
                "page": raw_pagination.get("page", 1),
                "page_size": raw_pagination.get("page_size", len(items)),
                "pages": raw_pagination.get("pages", 1),
                "count": raw_pagination.get("count", len(items)),
                "total": raw_pagination.get("total"),
                "filtered": raw_pagination.get("filtered"),
            }
        )
        return PaginatedResult[TModel](pagination=pagination, results=items)

    def get(
        self,
        query: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
        validate: bool = True,
        overwrite_endpoint: str | None = None,
        overwrite_schema: type[TModel] | None = None,
        **kwargs: Any,
    ) -> PaginatedResult[TModel]:
        """
        Fetch one specific page for this resource.

        Args:
            overwrite_schema: Schema to use for parsing. Defaults to ``self.schema``.
            overwrite_endpoint:
            query: Base query parameters.
            page: Page number to request. Defaults to ``1``.
            page_size: Number of items per page.
            validate: Whether to run Pydantic validation for each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            A ``PaginatedResult[TModel]`` containing only the requested page.
        """
        self._ensure_supported()
        q = self._merge_query(query, kwargs)
        q = dict(q or {})
        q.setdefault("page", page)
        q.setdefault("page_size", page_size)
        endpoint = overwrite_endpoint or self.endpoint
        schema =  overwrite_schema or self.schema
        data = self.client.get(endpoint, query=q)
        return self._to_paginated(data, validate=validate, schema=schema)

    def where(
        self,
        query: Dict[str, Any] | None = None,
        filter_fn: Callable[[TModel | dict], bool] | None = None,
        page_size: int = 50,
        validate: bool = True,
        overwrite_endpoint: str | None = None,
        overwrite_schema: type[TModel] | None = None,
        **kwargs: Any,
    ) -> APIQuery[TModel]:
        """
        Return a lazy iterator over this endpoint.

        The iterator fetches data page by page on demand. ``filter_fn`` is applied
        client-side to each yielded item.
        """
        self._ensure_supported()
        q = dict(query or {})
        q.update(kwargs)
        q = self._normalize_query(q)
        self._warn_unknown_filters(q)
        endpoint = overwrite_endpoint or self.endpoint
        schema =  overwrite_schema or self.schema

        return APIQuery(
            client=self.client,
            endpoint=endpoint,
            query=q,
            filter_fn=filter_fn,
            page_size=page_size,
            schema=schema,
            validate=validate
        )

    def all(
        self,
        query: Dict[str, Any] | None = None,
        filter_fn: Callable[[TModel | dict], bool] | None = None,
        page_size: int = 50,
        validate: bool = True,
        overwrite_endpoint: str | None = None,
        overwrite_schema: type[TModel] | None = None,
        **kwargs: Any,
    ) -> APIQuery[TModel]:
        """
        Alias for :meth:`where` — lazy iteration over every item on this endpoint.

        Several docstrings across the SDK already document ``client.<resource>.all()``
        as the idiomatic way to iterate all items; this method makes those examples work.
        """
        return self.where(
            query=query,
            filter_fn=filter_fn,
            page_size=page_size,
            validate=validate,
            overwrite_endpoint=overwrite_endpoint,
            overwrite_schema=overwrite_schema,
            **kwargs,
        )

    def get_all(
        self,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        overwrite_endpoint: str | None = None,
        overwrite_schema: type[TModel] | None = None,
        **kwargs: Any,
    ) -> PaginatedResult[TModel]:
        """
        Fetch all available pages for this resource.

        Args:
            overwrite_schema: Schema to use for parsing. Defaults to ``self.schema``.
            overwrite_endpoint:
            query: Base query parameters.
            page_size: Number of items per page requested from the API.
            validate: Whether to run Pydantic validation for each item.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            A single ``PaginatedResult[TModel]`` containing merged results.
        """
        self._ensure_supported()
        q = self._merge_query(query, kwargs)
        q.setdefault("page_size", page_size)
        endpoint = overwrite_endpoint or self.endpoint
        schema =  overwrite_schema or self.schema
        data = self.client.get_all(endpoint, query=q)
        return self._to_paginated(data, validate=validate, schema=schema)

    def export(
            self,
            query: Dict[str, Any] | None = None,
            file: str | Path | None = None,
            validate: bool = True,
            overwrite_endpoint: str | None = None,
            overwrite_schema: type[TModel] | None = None,
            raw: bool = False,
            **kwargs: Any,
    ) -> Path | list[BaseModel]:
        """
        Export resource data as CSV or as a list of parsed models.

        If ``export_endpoint`` is defined on the component, it is used instead of
        ``endpoint``. If ``export_schema`` is defined, it is used for parsing;
        otherwise ``schema`` is used as fallback.

        Args:
            overwrite_schema: Schema to use for parsing. Defaults to ``self.export_schema``.
            query: Base query parameters.
            file: Output CSV path. If ``None``, returns a list of models.
            validate: Whether to run full Pydantic validation on each item.
                      If ``False``, models are built without validation using
                      ``model_construct``.
            overwrite_endpoint: Override the export endpoint for this call.
            raw: Save the CSV exactly as Trapper sends it (its own header, column order and values)
                instead of parsing the rows and writing them with the SDK's column names, sorted
                alphabetically. Needs ``file``; ``validate`` and ``overwrite_schema`` do not apply.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``Path`` to the generated CSV when ``file`` is provided,
            otherwise ``list[BaseModel]`` with parsed or constructed models.

        Raises:
            ValueError: If ``raw`` is ``True`` and ``file`` is ``None``.
        """
        self._ensure_supported()
        if raw and file is None:
            raise ValueError("raw=True saves Trapper's CSV as it comes: give a file")
        q = self._merge_query(query, kwargs)
        endpoint = overwrite_endpoint or self.export_endpoint or self.endpoint

        if raw:
            return self.client.export_all(endpoint, query=q, file=file)
        target_schema = overwrite_schema or self.export_schema or self.schema


        raw_data = self.client.get_all(endpoint, query=q)
        rows_raw = raw_data.get("results", [])
        items = [self._to_model(row, validate=validate, schema=target_schema) for row in rows_raw]

        if file is None:
            return items

        output_path = self.client._select_file(file)
        rows = [item.model_dump(mode="json") for item in items]
        self.client._write_csv(rows, output_path)
        return output_path

    def find(
            self,
            pk: int | str,
            query: Dict[str, Any] | None = None,
            validate: bool = True,
            overwrite_endpoint: str | None = None,
            overwrite_schema: type[TModel] | None = None,

            **kwargs: Any,
    ) -> TModel:
        """
        Retrieve one item by primary key.

        Args:
            overwrite_schema: Schema to use for parsing. Defaults to ``self.schema``.
            overwrite_endpoint:
            pk: Resource primary key.
            query: Base query parameters.
            validate: Whether to run full Pydantic validation.
                      If False, the model is constructed without validation.
            **kwargs: Extra query params merged into ``query``.

        Returns:
            A typed model instance. If ``validate=True``, fields are fully
            validated. If ``validate=False``, the model is built directly
            from the raw payload without running Pydantic validators.
        """
        self._ensure_supported()
        q = self._merge_query(query, kwargs)
        endpoint = overwrite_endpoint or self.endpoint
        schema =  overwrite_schema or self.schema

        data = self.client.get_one(f"{endpoint.rstrip('/')}/{pk}", query=q)

        if isinstance(data, dict) and "results" in data:
            results = data.get("results", [])
            if not results:
                raise KeyError(f"No results found for pk={pk}")
            data = results[0]

        return self._to_model(data, validate=validate, schema=schema)


    def __repr__(self) -> str:
        """Return debug-friendly representation of the component.

        Returns:
            String with class name and configured endpoint.
        """
        return f"<{self.__class__.__name__} endpoint={self.endpoint!r}>"
