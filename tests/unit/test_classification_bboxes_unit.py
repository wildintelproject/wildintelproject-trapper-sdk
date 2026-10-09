"""Trapper's string-encoded bboxes, as the classification schemas parse them."""
from trapper_client.schemas.classifications import ClassificationResultRecordTrapper


def parse(value):
    return ClassificationResultRecordTrapper.parse_bboxes(value)


def test_a_null_among_the_boxes_is_dropped():
    boxes = parse("[[0.28, 0.07, 0.29, 0.19], null]")

    assert [(b.x, b.y, b.width, b.height) for b in boxes] == [(0.28, 0.07, 0.29, 0.19)]


def test_only_nulls_is_no_boxes():
    assert parse("[null]") is None
    assert parse("[]") is None
    assert parse("") is None
