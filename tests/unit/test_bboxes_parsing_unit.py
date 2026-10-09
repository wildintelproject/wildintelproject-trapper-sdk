"""Unit tests for the bboxes field of ClassificationResultRecordTrapper."""
from __future__ import annotations

import pytest

from trapper_client.schemas.classifications import ClassificationResultRecordTrapper

parse = ClassificationResultRecordTrapper.parse_bboxes


def test_boxes_are_parsed():
    boxes = parse("[[0.1, 0.2, 0.3, 0.4]]")
    assert (boxes[0].x, boxes[0].y, boxes[0].width, boxes[0].height) == (0.1, 0.2, 0.3, 0.4)


def test_null_entry_among_boxes_is_skipped():
    boxes = parse("[[0.1, 0.2, 0.3, 0.4], null]")
    assert len(boxes) == 1


@pytest.mark.parametrize("value", ["[null]", "[]", "", None])
def test_no_usable_boxes_gives_none(value):
    assert parse(value) is None
