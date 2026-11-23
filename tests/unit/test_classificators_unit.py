"""
Unit tests for ClassificatorsComponent and ClassificatorRecord schema.

All API calls are mocked — no real server needed.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import ComponentUnitTestBase
from trapper_client import ClassificatorTemplate, err
from trapper_client.components.classificators import ClassificatorsComponent
from trapper_client.schemas import ClassificatorCreate, ClassificatorRecord, SpeciesRecord


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


def test_endpoint_matches_server_route():
    """Regresión: el endpoint apuntaba a /api/classificators, sin el prefijo
    media_classification/ que registra la ruta real en el servidor Trapper
    (media_classification/urls.py), lo que provocaba un 404 siempre."""
    assert ClassificatorsComponent.endpoint == "/media_classification/api/classificators"


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


# ── create() ─────────────────────────────────────────────────────────────────

class TestCreate:

    @pytest.fixture
    def client(self):
        c = MagicMock()
        c.server_version = "v1"
        c.session_post_multipart.return_value = MagicMock(
            status_code=302, headers={"location": "/media_classification/classificator/update/41/"}
        )
        return c

    @pytest.fixture
    def component(self, client):
        comp = ClassificatorsComponent(client)
        comp.find = MagicMock(return_value=ClassificatorRecord(**{**VALID_RECORD, "pk": 41}))
        return comp

    def test_returns_the_classificator_named_in_the_redirect(self, component):
        clf = component.create(ClassificatorCreate(name="Mammals"))
        component.find.assert_called_once_with(41)
        assert clf.pk == 41

    def test_posts_the_prefixed_form(self, component, client):
        component.create(ClassificatorCreate(
            name="Mammals", template="tab", species=[1, 2, 3], tracked_species=[2], sex=True, age=True,
        ))
        endpoint = client.session_post_multipart.call_args.args[0]
        data = client.session_post_multipart.call_args.kwargs["data"]
        assert endpoint == "media_classification/classificator/create/"
        assert data == {
            "classificator-name": "Mammals",
            "classificator-template": "tab",
            "classificator-species": "1,2,3",
            "classificator-tracked_species": "2",
            "classificator-sex": "on",
            "classificator-age": "on",
        }

    def test_only_takes_the_model(self, component, client):
        with pytest.raises(TypeError, match="takes a ClassificatorCreate, not dict"):
            component.create({"name": "Mammals"})
        client.session_post_multipart.assert_not_called()

    def test_a_dict_is_turned_into_the_model_by_the_caller(self, component, client):
        component.create(ClassificatorCreate.model_validate({"name": " Mammals ", "template": "Tabbed"}))
        data = client.session_post_multipart.call_args.kwargs["data"]
        assert (data["classificator-name"], data["classificator-template"]) == ("Mammals", "tab")

    def test_rejected_form_reports_only_the_classificators_fields(self, component, client):
        client.session_post_multipart.return_value = MagicMock(status_code=200, text="<html/>")
        client._extract_form_field_errors.return_value = "name: Classificator with this Name already exists."
        with pytest.raises(err.APIError, match="status 200.*name: Classificator with this Name already exists"):
            component.create(ClassificatorCreate(name="Mammals"))
        assert client._extract_form_field_errors.call_args.args[1] == "classificator-"

    def test_rejected_form_returns_none_without_raise_on_error(self, component, client):
        client.session_post_multipart.return_value = MagicMock(status_code=200, text="<html/>")
        assert component.create(ClassificatorCreate(name="Mammals"), raise_on_error=False) is None
        component.find.assert_not_called()

    def test_no_pk_in_the_redirect_gives_none(self, component, client):
        client.session_post_multipart.return_value = MagicMock(
            status_code=302, headers={"location": "/media_classification/classificator/list/"}
        )
        assert component.create(ClassificatorCreate(name="Mammals")) is None

    def test_redirect_to_login_is_a_refusal(self, component, client):
        client.session_post_multipart.return_value = MagicMock(
            status_code=302, headers={"location": "/account/login/?next=/x"}
        )
        with pytest.raises(err.APIError, match="login page"):
            component.create(ClassificatorCreate(name="Mammals"))

    def test_not_available_on_v2(self, component, client):
        client.server_version = "v2"
        with pytest.raises(err.UnsupportedVersionError):
            component.create(ClassificatorCreate(name="Mammals"))
        client.session_post_multipart.assert_not_called()


class TestClassificatorCreate:
    """The input model: what ``create()`` validates before anything is sent."""

    def test_defaults_match_a_plain_form(self):
        c = ClassificatorCreate(name="N")
        assert c.template is ClassificatorTemplate.INLINE
        assert c.species == [] and c.tracked_species == []
        assert not any([c.sex, c.age, c.count_new, c.behaviour, c.individual_id, c.classification_confidence])

    def test_a_checkbox_is_posted_only_when_ticked(self):
        form = ClassificatorCreate(name="N", behaviour=True).to_form()
        assert form["classificator-behaviour"] == "on"
        assert "classificator-sex" not in form
        assert form["classificator-species"] == "" and form["classificator-tracked_species"] == ""

    def test_species_are_deduplicated_keeping_the_order(self):
        assert ClassificatorCreate(name="N", species=[3, 1, 3, 2]).species == [3, 1, 2]

    def test_species_can_be_given_as_objects_or_primary_keys(self):
        lynx, fox = SpeciesRecord(pk=1, english_name="Iberian lynx"), SpeciesRecord(pk=4)
        c = ClassificatorCreate(name="N", species=[lynx, 5, fox], tracked_species=[lynx, 5])
        assert c.species == [1, 5, 4] and c.tracked_species == [1, 5]
        assert c.to_form()["classificator-species"] == "1,5,4"

    def test_a_tracked_species_object_must_be_among_the_species(self):
        with pytest.raises(ValueError, match=r"tracked_species \[2\]"):
            ClassificatorCreate(name="N", species=[1], tracked_species=[SpeciesRecord(pk=2)])

    def test_tracked_species_can_be_anything_when_every_species_is_allowed(self):
        assert ClassificatorCreate(name="N", tracked_species=[9]).tracked_species == [9]

    @pytest.mark.parametrize("kwargs", [
        {"name": " "},
        {"name": "x" * 256},
        {"name": "N", "template": "grid"},
        {"name": "N", "species": [0]},
        {"name": "N", "species": [1, 2], "tracked_species": [3]},
        {"name": "N", "sex": "maybe"},
        {"name": "N", "unknown": 1},
    ])
    def test_invalid_values_are_rejected(self, kwargs):
        with pytest.raises(ValueError):
            ClassificatorCreate(**kwargs)

    @pytest.mark.parametrize("value", [ClassificatorTemplate.TAB, "tab", "TAB", "Tabbed", " tab "])
    def test_template_accepts_member_value_label_or_name(self, value):
        assert ClassificatorCreate(name="N", template=value).template is ClassificatorTemplate.TAB
