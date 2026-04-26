"""
Unit tests for UserClassificationsComponent and its schemas.

All API calls are mocked — no real server needed.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import ComponentUnitTestBase, paginated_response
from trapper_client.components.user_classifications import UserClassificationsComponent
from trapper_client.schemas import (
    UserClassificationRecord,
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
    schema = UserClassificationRecord
    # sin export_schema propio: el base usa self.schema como fallback
    export_schema = UserClassificationRecord
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


# ── UserClassificationRecord ──────────────────────────────────────────────────

class TestUserClassificationRecord:

    def test_parses_minimal_response(self):
        """El schema acepta la respuesta mínima sin campos opcionales."""
        result = UserClassificationRecord.model_validate(VALID_RECORD_MINIMAL)

        assert result.pk == 1
        assert result.owner == "Iñaki Fernández de Viana y González"
        assert result.classification == 17
        assert isinstance(result.resource, ResourceUser)

    def test_optional_fields_absent_default_to_none(self):
        """Los campos opcionales ausentes dan None, no error."""
        result = UserClassificationRecord.model_validate(VALID_RECORD_MINIMAL)

        assert result.collection is None
        assert result.updated_at is None
        assert result.created_at is None
        assert result.approved is None
        assert result.detail_data is None
        assert result.delete_data is None
        assert result.ai_provider is None

    def test_static_attrs_defaults_to_empty_dict(self):
        result = UserClassificationRecord.model_validate(VALID_RECORD_MINIMAL)

        assert result.static_attrs == {}

    def test_dynamic_attrs_defaults_to_empty_list(self):
        result = UserClassificationRecord.model_validate(VALID_RECORD_MINIMAL)

        assert result.dynamic_attrs == []

    def test_parses_full_response(self):
        """El schema acepta la respuesta completa con todos los campos."""
        result = UserClassificationRecord.model_validate(VALID_RECORD_FULL)

        assert result.pk == 2
        assert result.collection == 36
        assert result.approved is False
        assert len(result.dynamic_attrs) == 1
        assert isinstance(result.dynamic_attrs[0], UserObservationAttr)

    def test_dynamic_attrs_items_are_typed(self):
        result = UserClassificationRecord.model_validate(VALID_RECORD_FULL)

        assert all(isinstance(a, UserObservationAttr) for a in result.dynamic_attrs)

    def test_resource_is_typed(self):
        result = UserClassificationRecord.model_validate(VALID_RECORD_FULL)

        assert isinstance(result.resource, ResourceUser)
        assert result.resource.pk == 2379965
