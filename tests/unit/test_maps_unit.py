"""
Unit tests for MapsComponent and MapRecord schema.

All API calls are mocked — no real server needed.
"""
from __future__ import annotations

from tests.base_component_tests import ComponentUnitTestBase
from trapper_client.components.maps import MapsComponent
from trapper_client.schemas import MapRecord


# ── datos de prueba ───────────────────────────────────────────────────────────

VALID_RECORD = {
    "pk": 3,
    "slug": "donana-camera-traps",
    "description": "Camera trap deployments in Doñana",
    "center": {"type": "Point", "coordinates": [-6.4, 37.0]},
    "zoom": 12,
    "locate": False,
    "licence": "Open Database License",
    "modified_at": "2026-04-13T09:30:59+02:00",
    "tilelayer": {"url": "https://tiles.example.org/{z}/{x}/{y}.png"},
    "owner": "wildintel@uhu.es",
    "owner_profile": "/accounts/profile/wildintel@uhu.es/",
    "edit_status": "Editors",
    "share_status": "Public",
    "settings": {"scrollWheelZoom": True},
    "delete_data": "/geomap/map/1/delete/",
    "detail_data": "/geomap/map/donana-camera-traps_1",
}

VALID_RECORD_MINIMAL = {"pk": 1}


def test_endpoint_matches_server_route():
    """El endpoint debe apuntar a geomap/api/maps (geomap/urls.py), montado
    bajo el prefijo geomap/ en la raíz del servidor Trapper."""
    assert MapsComponent.endpoint == "geomap/api/maps"


# ── tests heredados (get / get_all / where / find / export) ──────────────────

class TestMapsComponent(ComponentUnitTestBase):
    component_class = MapsComponent
    schema = MapRecord
    export_schema = MapRecord
    find_pk = 3
    valid_item = VALID_RECORD
    valid_export_item = VALID_RECORD


# ── MapRecord ─────────────────────────────────────────────────────────────────

class TestMapRecord:

    def test_parses_full_record(self):
        result = MapRecord.model_validate(VALID_RECORD)

        assert result.pk == 3
        assert result.slug == "donana-camera-traps"
        assert result.owner == "wildintel@uhu.es"
        assert result.edit_status == "Editors"
        assert result.share_status == "Public"

    def test_parses_minimal_record(self):
        """El schema acepta registros sin ningún campo opcional."""
        result = MapRecord.model_validate(VALID_RECORD_MINIMAL)

        assert result.pk == 1
        assert result.slug is None
        assert result.owner is None
        assert result.center is None
