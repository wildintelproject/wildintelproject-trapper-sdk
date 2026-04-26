"""
Unit tests for ClassificationsMapComponent and its schemas.

All API calls are mocked — no real server needed.
"""
from __future__ import annotations

import pytest

from tests.base_component_tests import ComponentUnitTestBase
from trapper_client.components.classifications_map import ClassificationsMapComponent
from trapper_client.schemas import (
    ClassificationMapRecord,
    ResourceClassificationMap,
)


# ── datos de prueba ───────────────────────────────────────────────────────────

VALID_RECORD = {
    "pk": 23,
    "resource": {
        "pk": 23,
        "name": "IMG_0007",
        "resource_type": "I",
        "thumbnail_url": "/storage/resource/media/23/tfile/",
        "date_recorded": "2022-07-20T13:16:42+02:00",
        "deployment": "r0021-dona_00_01",
    },
    "static_attrs": {},
    "dynamic_attrs": [],
    "classify_data": "/media_classification/classify/23/",
    "project": 1,
}

VALID_RECORD_WITH_ATTRS = {
    "pk": 42,
    "resource": {
        "pk": 42,
        "name": "IMG_0042",
        "resource_type": "I",
        "thumbnail_url": "/storage/resource/media/42/tfile/",
        "date_recorded": "2023-05-10T09:30:00+02:00",
        "deployment": "r0001-wicp_0001",
    },
    "static_attrs": {"camera_model": "Bushnell"},
    "dynamic_attrs": [
        {"observation_type": "animal", "species": "Sus scrofa", "count": "1"},
    ],
    "classify_data": "/media_classification/classify/42/",
    "project": 3,
}


# ── tests heredados (get / get_all / where / find / export) ──────────────────

class TestClassificationsMapComponent(ComponentUnitTestBase):
    component_class = ClassificationsMapComponent
    schema = ClassificationMapRecord
    export_schema = ClassificationMapRecord
    find_pk = 23
    valid_item = VALID_RECORD
    valid_export_item = VALID_RECORD


# ── ResourceClassificationMap ─────────────────────────────────────────────────

class TestResourceClassificationMap:

    def test_parses_all_fields(self):
        result = ResourceClassificationMap.model_validate(VALID_RECORD["resource"])

        assert result.pk == 23
        assert result.name == "IMG_0007"
        assert result.resource_type == "I"
        assert result.date_recorded == "2022-07-20T13:16:42+02:00"

    def test_deployment_is_string(self):
        """deployment es deployment_id (string), no un pk entero."""
        result = ResourceClassificationMap.model_validate(VALID_RECORD["resource"])

        assert isinstance(result.deployment, str)
        assert result.deployment == "r0021-dona_00_01"

    def test_has_no_url_or_mime(self):
        """ResourceClassificationMap no tiene los campos url ni mime."""
        result = ResourceClassificationMap.model_validate(VALID_RECORD["resource"])

        assert not hasattr(result, "url")
        assert not hasattr(result, "mime")


# ── ClassificationMapRecord ───────────────────────────────────────────────────

class TestClassificationMapRecord:

    def test_parses_minimal_response(self):
        result = ClassificationMapRecord.model_validate(VALID_RECORD)

        assert result.pk == 23
        assert result.project == 1
        assert result.classify_data == "/media_classification/classify/23/"
        assert isinstance(result.resource, ResourceClassificationMap)

    def test_static_attrs_defaults_to_empty_dict(self):
        result = ClassificationMapRecord.model_validate(VALID_RECORD)

        assert result.static_attrs == {}

    def test_dynamic_attrs_defaults_to_empty_list(self):
        result = ClassificationMapRecord.model_validate(VALID_RECORD)

        assert result.dynamic_attrs == []

    def test_parses_record_with_attrs(self):
        result = ClassificationMapRecord.model_validate(VALID_RECORD_WITH_ATTRS)

        assert result.pk == 42
        assert result.static_attrs == {"camera_model": "Bushnell"}
        assert len(result.dynamic_attrs) == 1
        assert result.dynamic_attrs[0]["observation_type"] == "animal"

    def test_resource_is_typed(self):
        result = ClassificationMapRecord.model_validate(VALID_RECORD_WITH_ATTRS)

        assert isinstance(result.resource, ResourceClassificationMap)
        assert result.resource.deployment == "r0001-wicp_0001"
