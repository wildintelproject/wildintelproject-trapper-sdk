"""``Resource.date_recorded`` is a timezone-aware ``datetime``."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from trapper_client.schemas import Deployment, Resource
from trapper_client.schemas.base import read_datetime

CET = timezone(timedelta(hours=1))


def resource(**kw):
    return Resource.model_validate({"pk": 1, **kw})


class TestResource:

    def test_the_date_of_the_json(self):
        r = resource(date_recorded="2024-03-10T20:49:43.076845+01:00")
        assert r.date_recorded == datetime(2024, 3, 10, 20, 49, 43, 76845, tzinfo=CET)

    def test_the_other_spelling_and_utc(self):
        assert resource(date_recorded="2024-03-10T20:49:43+0100").date_recorded == datetime(2024, 3, 10, 20, 49, 43, tzinfo=CET)
        assert resource(date_recorded="2024-03-10T19:49:43Z").date_recorded == datetime(2024, 3, 10, 20, 49, 43, tzinfo=CET)

    def test_they_can_be_compared_and_sorted(self):
        rows = [resource(pk=i, date_recorded=d) for i, d in ((1, "2024-03-02T10:00:00+01:00"), (2, "2024-03-01T10:00:00+01:00"))]
        assert [r.pk for r in sorted(rows, key=lambda r: r.date_recorded)] == [2, 1]

    @pytest.mark.parametrize("empty", [None, "", "  "])
    def test_empty_is_none(self, empty):
        assert resource(date_recorded=empty).date_recorded is None

    def test_missing_is_none(self):
        assert resource().date_recorded is None

    def test_what_cannot_be_read_is_kept(self):
        assert resource(date_recorded="yesterday").date_recorded == "yesterday"

    def test_a_datetime_is_kept(self):
        moment = datetime(2024, 1, 1, tzinfo=CET)
        assert resource(date_recorded=moment).date_recorded == moment

    def test_json_dump_is_iso(self):
        assert resource(date_recorded="2024-03-10T20:49:43+01:00").model_dump(mode="json")["date_recorded"] == "2024-03-10T20:49:43+01:00"


class TestSharedHelper:

    def test_deployments_use_the_same_reader(self):
        assert Deployment.model_validate({"pk": 1, "start_date": "2024-01-01T00:00:00+0100"}).start_date == datetime(2024, 1, 1, tzinfo=CET)

    @pytest.mark.parametrize("value, expected", [
        ("2024-01-01T00:00:00+01:00", datetime(2024, 1, 1, tzinfo=CET)),
        (None, None), ("", None), ("soon", "soon"),
    ])
    def test_read_datetime(self, value, expected):
        assert read_datetime(value) == expected
