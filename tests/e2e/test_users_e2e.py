"""
End-to-end tests for UsersComponent against a real Trapper server.

Requires environment variables:
    WILDINTEL_BASE_URL, WILDINTEL_ACCESS_TOKEN, WILDINTEL_SMOKE_ENABLED=1

Optional:
    WILDINTEL_USER_PK  — pk of an existing user record
"""
from __future__ import annotations

from tests.base_component_tests import ComponentE2ETestBase
from trapper_client.components.users import UsersComponent
from trapper_client.schemas import UserRecord


class TestUsersComponentE2E(ComponentE2ETestBase):
    component_class = UsersComponent
    schema = UserRecord
    export_schema = UserRecord
    env_pk_var = "WILDINTEL_USER_PK"
