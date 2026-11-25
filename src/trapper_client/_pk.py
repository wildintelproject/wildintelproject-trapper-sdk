"""Primary-key parameters that also take the SDK object they stand for (issue #75)."""
from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, Tuple, Type, Union

Expected = Union[Type[Any], Tuple[Type[Any], ...]]


def as_pk(value: Any, expected: Expected, name: str = "pk", allow_text: bool = False) -> Any:
    """The primary key ``value`` stands for.

    An ``int``, a numeric string or an object of the ``expected`` type (its ``pk``) give the ``int``. ``None`` is
    kept (an optional parameter). With ``allow_text`` any other string is kept as it is (``find()`` takes them).

    Raises:
        TypeError: Anything else, or an object of another type (a ``Deployment`` where a classification project
            goes), before any request.
    """
    if value is None or (isinstance(value, int) and not isinstance(value, bool)):
        return value
    if isinstance(value, str):
        if value.strip().isdigit():
            return int(value)
        if allow_text:
            return value
    types = expected if isinstance(expected, tuple) else (expected,)
    if isinstance(value, types):
        pk = getattr(value, "pk", None)
        if isinstance(pk, int) and not isinstance(pk, bool):
            return pk
        raise TypeError(f"{name}: this {type(value).__name__} has no pk")
    names = " or ".join(t.__name__ for t in types)
    raise TypeError(f"{name} takes a primary key (int) or a {names}, not {type(value).__name__}: {value!r:.80}")


def takes_pk(**expected: Expected) -> Callable:
    """Let the named primary-key parameters of a method also take the object they stand for.

    ``@takes_pk(project_pk=ClassificationProject)``: ``method(project)`` is ``method(project.pk)``.
    """
    def decorate(method: Callable) -> Callable:
        signature = inspect.signature(method)
        missing = [name for name in expected if name not in signature.parameters]
        if missing:
            raise TypeError(f"{method.__qualname__} has no parameter {', '.join(missing)}")

        @functools.wraps(method)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            bound = signature.bind_partial(*args, **kwargs)
            for name, types in expected.items():
                if name in bound.arguments:
                    bound.arguments[name] = as_pk(bound.arguments[name], types, name)
            return method(*bound.args, **bound.kwargs)

        wrapper.__pk_types__ = expected  # type: ignore[attr-defined]
        return wrapper

    return decorate
