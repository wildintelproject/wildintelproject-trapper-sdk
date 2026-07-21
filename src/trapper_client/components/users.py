"""
Component for the Users data endpoint.
"""

from __future__ import annotations

from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import UserRecord


class UsersComponent(TrapperComponent[UserRecord]):
    """
    Component for ``/accounts/api/users``.

    Retrieve Trapper user accounts. Useful to resolve owner/user PKs (e.g.
    from ``owner`` filters on other components) to a username or display name.

    Main endpoints:
    - ``GET /accounts/api/users``: List of users (paginated)
    - ``GET /accounts/api/users/{pk}``: Single user detail

    No server-side filters are documented for this endpoint.
    """

    endpoint = "accounts/api/users"
    schema = UserRecord
