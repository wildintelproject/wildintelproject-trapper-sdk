"""
Component for the user accounts of Trapper.
"""

from __future__ import annotations

from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import User


class UsersComponent(TrapperComponent[User]):
    """
    The user accounts of Trapper (``client.users``), to turn the user PKs of other components (``owner``, ``user``)
    into a username or a name.

    - ``GET /accounts/api/users`` (and ``/{pk}``): every account of the server, paginated, for any user with a token.
      A row has ``username``, ``first_name``, ``last_name``, ``email`` and ``name`` (the full name, or the username).

    **No filters**: Trapper ignores every parameter (``search``, ``username``, ...) without an error and returns
    every user; the SDK emits an ``UnknownFilterWarning``. Filter on the client::

        ana = next(client.users.where(filter_fn=lambda u: u.username == "ana"))
    """

    endpoint = "accounts/api/users"
    schema = User
    known_filters = {"v1": frozenset(), "v2": frozenset()}
