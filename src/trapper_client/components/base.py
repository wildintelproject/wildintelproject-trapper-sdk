"""
Base class for all Trapper API components.
"""

from __future__ import annotations

import logging
import time
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
            **kwargs: Extra query params merged into ``query``.

        Returns:
            ``Path`` to the generated CSV when ``file`` is provided,
            otherwise ``list[BaseModel]`` with parsed or constructed models.
        """
        self._ensure_supported()
        q = self._merge_query(query, kwargs)
        endpoint = overwrite_endpoint or self.export_endpoint or self.endpoint
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
