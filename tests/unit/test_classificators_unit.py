"""
Unit tests for ClassificatorsComponent and ClassificatorRecord schema.

All API calls are mocked — no real server needed.
"""
from __future__ import annotations

from tests.base_component_tests import ComponentUnitTestBase
from trapper_client.components.classificators import ClassificatorsComponent
from trapper_client.schemas import ClassificatorRecord


# ── datos de prueba ───────────────────────────────────────────────────────────

VALID_RECORD = {
    "pk": 39,
    "name": "DeepFaune Classifier v1.3 (34 species) Doñana_wildintel@uhu.es_20260413_073059",
    "owner": "wildintel@uhu.es",
    "owner_profile": "/accounts/profile/wildintel@uhu.es/",
    "updated_date": "2026-04-13T09:30:59.058634+02:00",
    "predefined_attrs": {},
    "static_attrs_order": "is_setup",
    "custom_attrs": {},
    "dynamic_attrs_order": "observation_type,species,count",
    "description": "Auto-generated from AI Provider 'DeepFaune Classifier v1.3 (34 species) Doñana' species mapping on 2026-04-13 07:30:59",
    "update_data": "/media_classification/classificator/update/39/",
    "detail_data": "/media_classification/classificator/detail/39/",
    "delete_data": "/media_classification/classificator/delete/39/",
}

VALID_RECORD_MINIMAL = {
    "pk": 1,
    "name": "Manual Classifier",
    "owner": "admin@example.com",
    "owner_profile": "/accounts/profile/admin@example.com/",
    "updated_date": "2025-01-01T00:00:00+00:00",
    "update_data": "/media_classification/classificator/update/1/",
    "detail_data": "/media_classification/classificator/detail/1/",
    "delete_data": "/media_classification/classificator/delete/1/",
}


# ── tests heredados (get / get_all / where / find / export) ──────────────────

class TestClassificatorsComponent(ComponentUnitTestBase):
    component_class = ClassificatorsComponent
    schema = ClassificatorRecord
    export_schema = ClassificatorRecord
    find_pk = 39
    valid_item = VALID_RECORD
    valid_export_item = VALID_RECORD


# ── ClassificatorRecord ───────────────────────────────────────────────────────

class TestClassificatorRecord:

    def test_parses_full_record(self):
        result = ClassificatorRecord.model_validate(VALID_RECORD)

        assert result.pk == 39
        assert result.owner == "wildintel@uhu.es"
        assert result.static_attrs_order == "is_setup"
        assert result.dynamic_attrs_order == "observation_type,species,count"

    def test_parses_minimal_record(self):
        """El schema acepta registros sin los campos opcionales."""
        result = ClassificatorRecord.model_validate(VALID_RECORD_MINIMAL)

        assert result.pk == 1
        assert result.static_attrs_order is None
        assert result.dynamic_attrs_order is None
        assert result.description is None

    def test_predefined_attrs_defaults_to_empty_dict(self):
        result = ClassificatorRecord.model_validate(VALID_RECORD_MINIMAL)

        assert result.predefined_attrs == {}

    def test_custom_attrs_defaults_to_empty_dict(self):
        result = ClassificatorRecord.model_validate(VALID_RECORD_MINIMAL)

        assert result.custom_attrs == {}

    def test_action_urls_are_strings(self):
        result = ClassificatorRecord.model_validate(VALID_RECORD)

        assert result.update_data == "/media_classification/classificator/update/39/"
        assert result.detail_data == "/media_classification/classificator/detail/39/"
        assert result.delete_data == "/media_classification/classificator/delete/39/"

    def test_predefined_attrs_with_data(self):
        record = {**VALID_RECORD, "predefined_attrs": {"threshold": 0.5}}
        result = ClassificatorRecord.model_validate(record)

        assert result.predefined_attrs == {"threshold": 0.5}

    def test_custom_attrs_with_data(self):
        record = {**VALID_RECORD, "custom_attrs": {"region": "doñana"}}
        result = ClassificatorRecord.model_validate(record)

        assert result.custom_attrs == {"region": "doñana"}
