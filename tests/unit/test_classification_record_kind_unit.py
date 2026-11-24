"""The results row class is picked by its columns, not by which class happens to validate."""
from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from trapper_client.schemas.classifications import (
    ClassificationRecordExport,
    ClassificationResultRecordCamtrapDP,
    ClassificationResultRecordTrapper,
)

adapter = TypeAdapter(ClassificationRecordExport)

BASE = {
    "observationID": "4", "deploymentID": "don01-2024a", "mediaID": "5", "eventID": "",
    "eventStart": "2024-03-19T13:30:31+0100", "eventEnd": "2024-03-19T13:30:31+0100",
    "observationLevel": "media", "observationType": "animal", "scientificName": "Lynx pardinus",
}


def test_a_row_with_id_is_the_trapper_record_even_with_a_v2_box():
    """Before, a v2 box failed the Trapper class and the row came back as CamtrapDP with ``bboxes`` as text."""
    row = adapter.validate_python({**BASE, "_id": "6", "bboxes": "[0.6,0.6,0.2,0.2]"})
    assert isinstance(row, ClassificationResultRecordTrapper)
    assert row.bboxes[0].x == 0.6
    assert row.id == 6


def test_a_row_with_id_and_a_v1_list_of_boxes():
    row = adapter.validate_python({**BASE, "_id": "5", "bboxes": "[[0.12,0.11,0.3,0.3],[0.5,0.1,0.2,0.2]]"})
    assert isinstance(row, ClassificationResultRecordTrapper)
    assert len(row.bboxes) == 2


def test_a_row_without_id_is_the_camtrapdp_record():
    row = adapter.validate_python({**BASE, "bboxX": "0.6", "bboxY": "0.6", "bboxWidth": "0.2", "bboxHeight": "0.2"})
    assert isinstance(row, ClassificationResultRecordCamtrapDP)
    assert row.bboxX == 0.6


def test_a_trapper_row_with_an_unreadable_box_is_an_error_not_a_mistyped_row():
    with pytest.raises(ValidationError):
        adapter.validate_python({**BASE, "_id": "6", "bboxes": "[1, 2]"})
