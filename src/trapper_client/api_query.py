from __future__ import annotations

import re
import logging
from typing import TYPE_CHECKING, Callable, Iterator, Generic, TypeVar, Any

from pydantic import BaseModel, TypeAdapter

if TYPE_CHECKING:
    from trapper_client.api_client_base import APIClientBase

TModel = TypeVar("TModel", bound=BaseModel)
logger = logging.getLogger(__name__)


def parse_row(row: Any, schema: Any, validate: bool) -> Any:
    """Parse one raw API row into ``schema``.

    ``schema`` is usually a Pydantic model, but may also be a ``Union`` or
    ``Annotated`` type (e.g. ``ClassificationRecordExport``), which has no
    ``model_validate``/``model_construct``: those rows are always validated
    through a ``TypeAdapter``, since only validation can pick the Union member.

    Args:
        row: Raw row payload from the API.
        schema: Pydantic model or type the row is parsed into.
        validate: Whether to run full Pydantic validation (models only).

    Returns:
        The parsed row (``row`` itself if it's already an instance of ``schema``).
    """
    if not (isinstance(schema, type) and issubclass(schema, BaseModel)):
        return TypeAdapter(schema).validate_python(row)
    if isinstance(row, schema):
        return row
    if validate:
        return schema.model_validate(row)
    if isinstance(row, dict):
        return schema.model_construct(**row)
    return schema.model_construct(raw=row)


class APIQuery(Generic[TModel], Iterator[TModel | dict]):
    """Lazy iterator with transparent API pagination.

    Fetches pages on demand from an endpoint, optionally resolves endpoint
    placeholders (for example ``{project_pk}``), and yields row items one by one.

    Args:
        client: API client instance exposing ``get``.
        endpoint: API endpoint path, optionally with ``{placeholder}`` segments.
        query: Base query parameters.
        schema: Optional Pydantic schema used to parse each page response.
        filter_fn: Optional client-side item predicate.
        page_size: Number of items requested per API page.
    """

    def __init__(
        self,
        client: "APIClientBase",
        endpoint: str,
        query: dict[str, Any] | None = None,
        schema: type[TModel] | None = None,
        filter_fn: Callable[[TModel | dict], bool] | None = None,
        page_size: int = 50,
        validate: bool = True
    ):
        self.client = client
        self.endpoint = endpoint
        self.query = {} if query is None else query.copy()
        self.schema = schema
        self.filter_fn = filter_fn

        self._page_size = page_size
        self._page = 0
        self._pages = 1
        self._last_results: list[TModel | dict] = []
        self._last_index = 0
        self._exhausted = False
        self.validate = validate

    def __iter__(self) -> "APIQuery[TModel]":
        """Return the iterator itself.

        Returns:
            ``self``.
        """
        return self

    def __next__(self) -> TModel | dict:
        """Return the next available item, loading pages lazily.

        Returns:
            Next row as dict or parsed model.

        Raises:
            StopIteration: When no more items are available.
        """
        if self._exhausted:
            raise StopIteration

        while True:
            # Load next page if current buffer is exhausted
            if self._last_index >= len(self._last_results):
                if self._page >= self._pages:
                    self._exhausted = True
                    raise StopIteration

                page_query = self.query.copy()
                page_query["page"] = self._page + 1
                page_query["page_size"] = self._page_size

                # Resolve placeholders like {id} in the endpoint
                endpoint_resolved = self.endpoint
                for key in re.findall(r"\{([^}]+)\}", self.endpoint):
                    if key in page_query:
                        endpoint_resolved = endpoint_resolved.replace(
                            "{" + key + "}", str(page_query.pop(key))
                        )

                logger.debug(f"Loading page {page_query['page']} from {endpoint_resolved}")
                response = self.client.get(endpoint_resolved, page_query, raise_on_error=True)
                raw_results = response.get("results", [])

                if self.schema:
                    self._last_results = [parse_row(row, self.schema, self.validate) for row in raw_results]
                else:
                    self._last_results = raw_results

                pagination = response.get("pagination", {"page": -1, "pages": 1})

                if not self._last_results:
                    self._exhausted = True
                    raise StopIteration

                self._page = int(pagination.get("page", -1))
                self._pages = int(pagination.get("pages", 1))
                self._last_index = 0

            # Fetch next raw item from buffer
            raw_item = self._last_results[self._last_index]
            self._last_index += 1

            # Apply local filter if provided
            if not self.filter_fn or self.filter_fn(raw_item):
                logger.debug(f"Returning item from page {self._page}: {raw_item}")
                return raw_item
            # Otherwise continue to fetch the next item

    def close(self) -> None:
        """Mark iterator as exhausted and clear internal buffers.

        Returns:
            ``None``.
        """
        self._exhausted = True
        self._last_results = []
        self._last_index = 0
        self._pages = 0
        self._page = -1

    def __enter__(self) -> "APIQuery[TModel]":
        """Enter context manager.

        Returns:
            ``self``.
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        """Exit context manager and close iterator safely.

        Args:
            exc_type: Exception type, if raised in context.
            exc_value: Exception instance, if raised in context.
            traceback: Exception traceback, if raised in context.

        Returns:
            ``False`` to avoid suppressing exceptions.
        """
        try:
            self.close()
        except Exception:
            pass
        return False

