"""
Unit tests for UserClassificationsComponent and its schemas.

All API calls are mocked — no real server needed.
"""
from __future__ import annotations

import warnings as _warnings
from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import ComponentUnitTestBase, paginated_response
from trapper_client import err as _err
from trapper_client.components.ai_classifications import AIClassificationsComponent as _AI
from trapper_client.components.user_classifications import UserClassificationsComponent
from trapper_client.schemas import (
    UserClassification,
    UserObservationAttr,
    ResourceUser,
)


# ── datos de prueba ───────────────────────────────────────────────────────────

VALID_RECORD_MINIMAL = {
    "pk": 1,
    "owner": "Iñaki Fernández de Viana y González",
    "owner_profile": "/accounts/profile/i.fviana@dti.uhu.es/",
    "classification": 17,
    "resource": {
        "pk": 17,
        "name": "IMG_0001",
        "resource_type": "I",
        "thumbnail_url": "/storage/resource/media/17/tfile/",
        "url": "/storage/resource/media/17/pfile/",
        "mime": "image/jpeg",
        "date_recorded": "2022-07-20T12:56:32+02:00",
        "deployment": 1,
        "deployment_id": "r0021-dona_00_01",
    },
}

VALID_RECORD_FULL = {
    "pk": 2,
    "owner": "Pedro Garcia",
    "owner_profile": "/accounts/profile/pedro.garcia@dci.uhu.es/",
    "classification": 480196,
    "resource": {
        "pk": 2379965,
        "name": "R9999-DONA_9999__20041124_1.JPEG",
        "resource_type": "I",
        "thumbnail_url": "/storage/resource/media/2379965/tfile/",
        "url": "/storage/resource/media/2379965/pfile/",
        "mime": "image/jpeg",
        "date_recorded": "2004-11-24T07:22:00+01:00",
        "deployment": 658,
        "deployment_id": "r9999-dona_9999",
    },
    "collection": 36,
    "updated_at": "2025-10-01T13:51:16.385117+02:00",
    "created_at": "2025-10-01T13:51:16.385116+02:00",
    "approved": False,
    "static_attrs": {},
    "dynamic_attrs": [
        {
            "observation_type": "animal",
            "species": "Sus scrofa",
            "count": "2",
            "classification_confidence": "0.87",
        }
    ],
    "detail_data": "/media_classification/classify/480196/user/2/",
    "delete_data": "/media_classification/user_classifications/delete/2/",
    "ai_provider": "",
}


# ── tests heredados (get / get_all / where / find / export) ──────────────────

class TestUserClassificationsComponent(ComponentUnitTestBase):
    component_class = UserClassificationsComponent
    schema = UserClassification
    # sin export_schema propio: el base usa self.schema como fallback
    export_schema = UserClassification
    find_pk = 1
    valid_item = VALID_RECORD_MINIMAL
    valid_export_item = VALID_RECORD_MINIMAL


# ── ResourceUser ──────────────────────────────────────────────────────────────

class TestResourceUser:

    def test_parses_all_fields(self):
        result = ResourceUser.model_validate(VALID_RECORD_MINIMAL["resource"])

        assert result.pk == 17
        assert result.name == "IMG_0001"
        assert result.resource_type == "I"
        assert result.deployment == 1
        assert result.deployment_id == "r0021-dona_00_01"

    def test_thumbnail_and_url_are_strings(self):
        result = ResourceUser.model_validate(VALID_RECORD_MINIMAL["resource"])

        assert isinstance(result.thumbnail_url, str)
        assert isinstance(result.url, str)


# ── UserObservationAttr ───────────────────────────────────────────────────────

class TestUserObservationAttr:

    def test_parses_all_fields(self):
        data = {
            "observation_type": "animal",
            "species": "Sus scrofa",
            "count": "2",
            "classification_confidence": "0.87",
        }
        result = UserObservationAttr.model_validate(data)

        assert result.observation_type == "animal"
        assert result.species == "Sus scrofa"
        assert result.count == "2"
        assert result.classification_confidence == "0.87"

    def test_optional_fields_default_to_none(self):
        result = UserObservationAttr(observation_type="blank")

        assert result.species is None
        assert result.count is None
        assert result.classification_confidence is None


# ── UserClassification ──────────────────────────────────────────────────

class TestUserClassificationRecord:

    def test_parses_minimal_response(self):
        """El schema acepta la respuesta mínima sin campos opcionales."""
        result = UserClassification.model_validate(VALID_RECORD_MINIMAL)

        assert result.pk == 1
        assert result.owner == "Iñaki Fernández de Viana y González"
        assert result.classification == 17
        assert isinstance(result.resource, ResourceUser)

    def test_optional_fields_absent_default_to_none(self):
        """Los campos opcionales ausentes dan None, no error."""
        result = UserClassification.model_validate(VALID_RECORD_MINIMAL)

        assert result.collection is None
        assert result.updated_at is None
        assert result.created_at is None
        assert result.approved is None
        assert result.detail_data is None
        assert result.delete_data is None
        assert result.ai_provider is None

    def test_static_attrs_defaults_to_empty_dict(self):
        result = UserClassification.model_validate(VALID_RECORD_MINIMAL)

        assert result.static_attrs == {}

    def test_dynamic_attrs_defaults_to_empty_list(self):
        result = UserClassification.model_validate(VALID_RECORD_MINIMAL)

        assert result.dynamic_attrs == []

    def test_parses_full_response(self):
        """El schema acepta la respuesta completa con todos los campos."""
        result = UserClassification.model_validate(VALID_RECORD_FULL)

        assert result.pk == 2
        assert result.collection == 36
        assert result.approved is False
        assert len(result.dynamic_attrs) == 1
        assert isinstance(result.dynamic_attrs[0], UserObservationAttr)

    def test_dynamic_attrs_items_are_typed(self):
        result = UserClassification.model_validate(VALID_RECORD_FULL)

        assert all(isinstance(a, UserObservationAttr) for a in result.dynamic_attrs)

    def test_resource_is_typed(self):
        result = UserClassification.model_validate(VALID_RECORD_FULL)

        assert isinstance(result.resource, ResourceUser)
        assert result.resource.pk == 2379965


# ── filters by version and project (issue #105) ──────────────────────────────

def _component(cls, version):
    client = MagicMock()
    client.server_version = version
    client.get.return_value = paginated_response([])
    client.get_all.return_value = paginated_response([])
    return cls(client)


@pytest.mark.parametrize("cls", [UserClassificationsComponent, _AI])
@pytest.mark.parametrize("call", ["get", "where", "get_all"])
def test_deployment_and_collection_need_project(cls, call):
    component = _component(cls, "v2")
    with pytest.raises(ValueError, match="need project=<pk>"):
        getattr(component, call)(deployment=3)
    with pytest.raises(ValueError, match="deployment and collection"):
        getattr(component, call)(deployment=3, collection=1)


@pytest.mark.parametrize("cls", [UserClassificationsComponent, _AI])
def test_with_project_there_is_no_error(cls):
    _component(cls, "v1").get(deployment=3, project=2)


@pytest.mark.parametrize(
    "cls, version, name, warns",
    [
        (UserClassificationsComponent, "v1", "sex", True),
        (UserClassificationsComponent, "v2", "sex", False),
        (UserClassificationsComponent, "v1", "classified", True),
        (UserClassificationsComponent, "v1", "feedback", False),
        (_AI, "v1", "rdate_from", True),
        (_AI, "v1", "user", True),
        (_AI, "v2", "rdate_from", False),
        (_AI, "v1", "confidence", False),
        (_AI, "v1", "search", False),
        (_AI, "v2", "nonsense", True),
    ],
)
def test_filters_trapper_ignores_warn(cls, version, name, warns):
    component = _component(cls, version)
    with _warnings.catch_warnings(record=True) as caught:
        _warnings.simplefilter("always")
        component.get(**{name: "x"})
    found = [w for w in caught if issubclass(w.category, _err.UnknownFilterWarning)]
    assert bool(found) is warns


def test_approved_in_the_v2_ai_table_warns():
    component = _component(_AI, "v2")
    with pytest.warns(_err.UnknownFilterWarning, match="answers 500 to 'approved'"):
        component.export(2, approved=True)


def test_approved_in_the_v1_ai_table_does_not_warn():
    component = _component(_AI, "v1")
    with _warnings.catch_warnings():
        _warnings.simplefilter("error", _err.UnknownFilterWarning)
        component.export(2, approved=True)


@pytest.mark.parametrize("call", ["get", "where", "get_all"])
def test_the_warning_points_at_the_caller(call):
    """Not at a line of the SDK, whatever the number of SDK functions in between (mixins, where → get)."""
    component = _component(UserClassificationsComponent, "v1")
    with pytest.warns(_err.UnknownFilterWarning) as caught:
        getattr(component, call)(nonsense=1)
    assert caught[0].filename == __file__
