"""
Unit tests for SpeciesComponent and SpeciesRecord schema.

All API calls are mocked — no real server needed.
"""
from __future__ import annotations

from tests.base_component_tests import ComponentUnitTestBase
from trapper_client.components.species import SpeciesComponent
from trapper_client.schemas import SpeciesRecord


# ── datos de prueba ───────────────────────────────────────────────────────────

VALID_RECORD = {
    "pk": 5,
    "__str__": "Wolf (Canis lupus)",
    "english_name": "Wolf",
    "latin_name": "Canis lupus",
    "genus": "Canis",
    "family": "Canidae",
}

VALID_RECORD_MINIMAL = {
    "pk": 1,
    "english_name": "Unknown",
    "latin_name": "",
}


def test_endpoint_matches_server_route():
    """El endpoint debe apuntar a tables/api/species (extra_tables/urls.py),
    montado bajo el prefijo tables/ en la raíz del servidor Trapper."""
    assert SpeciesComponent.endpoint == "tables/api/species"


# ── tests heredados (get / get_all / where / find / export) ──────────────────

class TestSpeciesComponent(ComponentUnitTestBase):
    component_class = SpeciesComponent
    schema = SpeciesRecord
    export_schema = SpeciesRecord
    find_pk = 5
    valid_item = VALID_RECORD
    valid_export_item = VALID_RECORD


# ── SpeciesRecord ─────────────────────────────────────────────────────────────

class TestSpeciesRecord:

    def test_parses_full_record(self):
        result = SpeciesRecord.model_validate(VALID_RECORD)

        assert result.pk == 5
        assert result.english_name == "Wolf"
        assert result.latin_name == "Canis lupus"
        assert result.genus == "Canis"
        assert result.family == "Canidae"

    def test_str_field_is_exposed_as_display_name(self):
        """El servidor serializa __str__() del modelo bajo la clave literal
        '__str__' (DRF); el schema la expone como display_name via alias."""
        result = SpeciesRecord.model_validate(VALID_RECORD)

        assert result.display_name == "Wolf (Canis lupus)"

    def test_parses_minimal_record(self):
        """El schema acepta registros sin family/genus/__str__."""
        result = SpeciesRecord.model_validate(VALID_RECORD_MINIMAL)

        assert result.pk == 1
        assert result.genus is None
        assert result.family is None
        assert result.display_name is None

    def test_display_name_populatable_by_field_name(self):
        """populate_by_name permite construir el modelo con display_name= además
        del alias __str__, útil para tests/código que no reciben el payload crudo."""
        result = SpeciesRecord(pk=1, display_name="Test (Testus)")

        assert result.display_name == "Test (Testus)"
