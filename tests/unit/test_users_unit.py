"""
Unit tests for UsersComponent and UserRecord schema.

All API calls are mocked — no real server needed.
"""
from __future__ import annotations

from tests.base_component_tests import ComponentUnitTestBase
from trapper_client.components.users import UsersComponent
from trapper_client.schemas import UserRecord


# ── datos de prueba ───────────────────────────────────────────────────────────

VALID_RECORD = {
    "pk": 7,
    "username": "wildintel",
    "first_name": "Wild",
    "last_name": "Intel",
    "email": "wildintel@uhu.es",
    "name": "Wild Intel",
}

VALID_RECORD_MINIMAL = {"pk": 1, "username": "anon"}


def test_endpoint_matches_server_route():
    """El endpoint debe apuntar a accounts/api/users (accounts/urls.py),
    montado bajo el prefijo accounts/ en la raíz del servidor Trapper."""
    assert UsersComponent.endpoint == "accounts/api/users"


# ── tests heredados (get / get_all / where / find / export) ──────────────────

class TestUsersComponent(ComponentUnitTestBase):
    component_class = UsersComponent
    schema = UserRecord
    export_schema = UserRecord
    find_pk = 7
    valid_item = VALID_RECORD
    valid_export_item = VALID_RECORD


# ── UserRecord ────────────────────────────────────────────────────────────────

class TestUserRecord:

    def test_parses_full_record(self):
        result = UserRecord.model_validate(VALID_RECORD)

        assert result.pk == 7
        assert result.username == "wildintel"
        assert result.name == "Wild Intel"

    def test_parses_minimal_record(self):
        """El schema acepta registros sin first_name/last_name/email/name."""
        result = UserRecord.model_validate(VALID_RECORD_MINIMAL)

        assert result.pk == 1
        assert result.username == "anon"
        assert result.first_name is None
        assert result.name is None
