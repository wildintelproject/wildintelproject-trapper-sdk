"""
Base class for all Trapper API components.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Generic, TypeVar, Union

from pydantic import BaseModel, TypeAdapter

from trapper_client.api_query import APIQuery
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

    def __init__(self, client: "APIClientBase"):
        self.client = client

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
        target = schema or self.schema
        # isinstance falla con Union/Annotated — solo comprobamos si es clase concreta
        try:
            if isinstance(row, target):
                return row
        except TypeError:
            pass  # target es Union o Annotated, no se puede usar con isinstance

        if validate:
            try:
                return target.model_validate(row)
            except AttributeError:
                return TypeAdapter(target).validate_python(row)
        if isinstance(row, dict):
            try:
                return target.model_construct(**row)
            except AttributeError:
                return TypeAdapter(target).validate_python(row)
        try:
            return target.model_construct(raw=row)
        except AttributeError:
            return TypeAdapter(target).validate_python(row)

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
        **kwargs,
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
        **kwargs,
    ) -> APIQuery[TModel]:
        """
        Return a lazy iterator over this endpoint.

        The iterator fetches data page by page on demand. ``filter_fn`` is applied
        client-side to each yielded item.
        """
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

    def get_all(
        self,
        query: Dict[str, Any] | None = None,
        page_size: int = 50,
        validate: bool = True,
        overwrite_endpoint: str | None = None,
        overwrite_schema: type[TModel] | None = None,
        **kwargs,
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
            **kwargs,
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

            **kwargs,
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
