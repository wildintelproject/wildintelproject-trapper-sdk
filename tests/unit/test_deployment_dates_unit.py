"""The dates of a deployment are timezone-aware ``datetime`` in the list and in the export."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from trapper_client.schemas import Deployment, DeploymentExport

CET = timezone(timedelta(hours=1))


def listed(**kw):
    return Deployment.model_validate({"pk": 1, **kw})


def exported(**kw):
    return DeploymentExport.model_validate({"_id": 1, **kw})


class TestRead:

    def test_json_with_a_colon_in_the_offset(self):
        assert listed(start_date="2024-01-01T00:00:00+01:00").start_date == datetime(2024, 1, 1, tzinfo=CET)

    def test_csv_without_a_colon_in_the_offset(self):
        assert exported(deploymentStart="2024-01-01T00:00:00+0100").start_date == datetime(2024, 1, 1, tzinfo=CET)

    def test_the_two_spellings_are_the_same_instant(self):
        a = listed(start_date="2024-07-01T10:00:00+02:00", end_date="2024-07-02T10:00:00+02:00")
        b = exported(deploymentStart="2024-07-01T10:00:00+0200", deploymentEnd="2024-07-02T10:00:00+0200")
        assert a.start_date == b.start_date and a.end_date == b.end_date
        assert b.end_date - b.start_date == timedelta(days=1)

    def test_utc_and_z(self):
        for text in ("2024-01-01T00:00:00Z", "2024-01-01T00:00:00+00:00", "2024-01-01T00:00:00+0000"):
            assert exported(deploymentStart=text).start_date == datetime(2024, 1, 1, tzinfo=timezone.utc)

    def test_they_can_be_compared_and_sorted(self):
        rows = [exported(deploymentID=i, deploymentStart=s) for i, s in
                (("b", "2024-03-01T00:00:00+0100"), ("a", "2024-01-01T00:00:00+0100"))]
        assert [r.deployment_id for r in sorted(rows, key=lambda r: r.start_date)] == ["a", "b"]

    def test_a_datetime_is_kept(self):
        moment = datetime(2024, 1, 1, tzinfo=CET)
        assert listed(start_date=moment).start_date == moment
        assert exported(deploymentStart=moment).start_date == moment

    @pytest.mark.parametrize("empty", [None, "", "   "])
    def test_empty_is_none(self, empty):
        assert listed(start_date=empty, end_date=empty).end_date is None
        assert exported(deploymentStart=empty, deploymentEnd=empty).start_date is None

    def test_a_date_without_time_is_read(self):
        assert exported(deploymentStart="2024-01-01").start_date == datetime(2024, 1, 1)

    def test_what_cannot_be_read_is_kept_not_an_error(self):
        assert listed(start_date="soon").start_date == "soon"
        assert exported(deploymentStart="soon").start_date == "soon"

    def test_no_dates_no_problem(self):
        assert listed().start_date is None and exported().start_date is None


class TestWrite:

    def test_model_dump_json_gives_iso_with_a_colon(self):
        assert exported(deploymentStart="2024-01-01T00:00:00+0100").model_dump(mode="json")["start_date"] == \
            "2024-01-01T00:00:00+01:00"

    def test_a_dumped_row_reads_back_the_same(self):
        row = exported(deploymentID="d", deploymentStart="2024-01-01T00:00:00+0100", deploymentEnd="2024-02-01T00:00:00+0100")
        again = DeploymentExport.model_validate(row.model_dump(mode="json"))
        assert (again.start_date, again.end_date) == (row.start_date, row.end_date)
