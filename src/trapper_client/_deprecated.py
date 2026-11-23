"""Old schema names that still work, with a deprecation warning.

The schemas the API returns used to carry a ``Record`` suffix on some resources and not on
others (``SpeciesRecord`` next to ``ResearchProject``). They are now named after the resource.
Every old name is still importable, from the package, from ``trapper_client.schemas`` and from the
module that defines it, and gives the very same class as the new one: nothing breaks, but
importing an old name warns.

A module opts in with one line at its end::

    __getattr__ = deprecated_getattr(__name__)

The old names are not in any ``__all__``, so ``from trapper_client import *`` does not offer them.
"""
from __future__ import annotations

import sys
import warnings
from typing import Any, Callable

#: old name -> new name
RENAMED_SCHEMAS: dict[str, str] = {
    "UserRecord": "User",
    "SpeciesRecord": "Species",
    "SequenceRecord": "Sequence",
    "MapRecord": "Map",
    "ClassificatorRecord": "Classificator",
    "ClassificationRecord": "Classification",
    "UserClassificationRecord": "UserClassification",
    "AIClassificationRecord": "AIClassification",
    "ClassificationMapRecord": "ClassificationMap",
    "ClassificationAggRecord": "ClassificationAgg",
    "ClassificationResourceRecord": "ClassifiedResource",
    "MediaRecord": "Media",
}


def deprecated_getattr(module_name: str) -> Callable[[str], Any]:
    """A module ``__getattr__`` that resolves the old names of the schemas the module defines."""

    def __getattr__(name: str) -> Any:
        module = sys.modules[module_name]
        new = RENAMED_SCHEMAS.get(name)
        if new is None or new not in vars(module):
            raise AttributeError(f"module {module_name!r} has no attribute {name!r}")
        warnings.warn(
            f"{name} is deprecated and will be removed in a future release; use {new}",
            DeprecationWarning,
            stacklevel=2,
        )
        return vars(module)[new]

    return __getattr__
