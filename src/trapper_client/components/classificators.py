"""
Component for Classificators data endpoint.
"""

from __future__ import annotations

from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import ClassificatorRecord


class ClassificatorsComponent(TrapperComponent[ClassificatorRecord]):
    """
    Component for ``/api/classificators/``.

    Retrieve and filter classificators (AI/human classifier configurations) from Trapper.

    Main endpoints:
    - ``GET /api/classificators``: List of classificators (paginated)
    - ``GET /api/classificators/{pk}``: Single classificator detail

    **Available filter fields:**

    | Parameter  | Type    | Description                               |
    |------------|---------|-------------------------------------------|
    | owner      | boolean | true = classificators owned by the user   |
    | search     | string  | Search by name or description             |

    Returns a paginated list of classificators with support for filtering
    through query parameters.
    """

    endpoint = "/api/classificators"
    schema = ClassificatorRecord
