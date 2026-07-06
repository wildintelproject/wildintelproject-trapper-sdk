"""
trapper_api_client — Python client for the Trapper API.
"""

from trapper_client.api_client_base import APIClientBase
from trapper_client.api_query import APIQuery
from trapper_client.trapper_client import TrapperClient
from trapper_client import err

# Re-export every component and schema declared by the sub-packages' own
# __all__, instead of hand-duplicating a third list here. Components and
# schemas are added often enough that a manually curated copy always went
# stale (this file used to only export the first ~7 components ever added).
from trapper_client.components import *  # noqa: F401,F403
from trapper_client.components import __all__ as _components_all
from trapper_client.schemas import *  # noqa: F401,F403
from trapper_client.schemas import __all__ as _schemas_all

__all__ = [
    "APIClientBase",
    "APIQuery",
    "TrapperClient",
    "err",
    *sorted(set(_components_all) | set(_schemas_all)),
]
