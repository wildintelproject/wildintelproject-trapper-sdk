"""
Schemas must parse payloads captured from a real Trapper v2 server (2.0.0a).

v2 returns ``null`` for the UI link fields (``*_data``, ``owner_profile``), drops ``status``/``status_ai`` and
``classification``, and wraps user-classification attributes as ``{"value": ...}``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from trapper_client.schemas.classifications import ClassificationProject, ClassificationRecord
from trapper_client.schemas.classifications_map import ClassificationMapRecord
from trapper_client.schemas.classificators import ClassificatorRecord
from trapper_client.schemas.user_classifications import UserClassificationRecord, UserObservationAttr

PAYLOADS = json.loads((Path(__file__).parent / "data" / "trapper_v2_payloads.json").read_text(encoding="utf-8"))

SCHEMAS = {
    "classification_projects": ClassificationProject,
    "classification_results": ClassificationRecord,
    "classifications_map": ClassificationMapRecord,
    "classificators": ClassificatorRecord,
    "user_classifications": UserClassificationRecord,
}


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_real_v2_rows_validate(name):
    for row in PAYLOADS[name]:
        SCHEMAS[name].model_validate(row)


def test_v2_user_classification_attrs_are_unwrapped():
    record = UserClassificationRecord.model_validate(PAYLOADS["user_classifications"][0])
    attr = record.dynamic_attrs[0]
    assert isinstance(attr.observation_type, str)
    assert isinstance(attr.count, str)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ({"observation_type": {"value": "animal"}, "species": {"value": "Lynx"}, "count": {"value": "2"}}, ("animal", "Lynx", "2")),
        ({"observation_type": "animal", "species": "Lynx", "count": "2"}, ("animal", "Lynx", "2")),  # v1 shape
    ],
)
def test_attrs_accept_v1_and_v2_shapes(raw, expected):
    a = UserObservationAttr.model_validate(raw)
    assert (a.observation_type, a.species, a.count) == expected


def test_v1_only_fields_are_optional():
    row = dict(PAYLOADS["classification_results"][0])
    row.pop("approved", None)
    record = ClassificationRecord.model_validate(row)
    assert record.status is None and record.status_ai is None
