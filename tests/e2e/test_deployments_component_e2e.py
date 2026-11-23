"""
End-to-end tests for LocationsComponent.

Requires environment variables:
    WILDINTEL_BASE_URL, WILDINTEL_ACCESS_TOKEN, WILDINTEL_SMOKE_ENABLED=1

Optional:
    WILDINTEL_LOCATION_PK — pk of an existing location (for find tests)
"""
import csv

import pytest

from tests.base_component_tests import ComponentE2ETestBase
from trapper_client import DeploymentsComponent, LocationsComponent
from trapper_client.schemas import Deployment, DeploymentExport


class TestLocationsComponentE2E(ComponentE2ETestBase):
    component_class = DeploymentsComponent
    schema = Deployment
    export_schema = DeploymentExport
    env_pk_var = "WILDINTEL_DEPLOYMENT_PK"

    @pytest.mark.e2e
    def test_export_reads_the_tags_trapper_puts_in_deploymenttags(self, component, tmp_path):
        """The tags of the export are the ones of the CSV (``deploymentTags``), on v1 and v2."""
        raw_path = component.export(file=tmp_path / "raw.csv", raw=True)
        raw = {int(r["_id"]): r for r in csv.DictReader(raw_path.open(encoding="utf-8"))}
        parsed = {row.pk: row for row in component.export(file=None)}
        assert parsed.keys() == raw.keys()
        for pk, line in raw.items():
            names = [t.strip() for t in line["deploymentTags"].split("|") if t.strip() and not t.strip().startswith("baitType:")]
            assert parsed[pk].tags == names
            assert "deploymentTags" not in (parsed[pk].model_extra or {})
        if not any(line["deploymentTags"] for line in raw.values()):
            pytest.skip("No deployment with tags on this server")

    @pytest.mark.e2e
    def test_unknown_filter_warns_and_a_known_one_does_not(self, component):
        """The filters the warning knows are the ones this server applies (checked on v1 and v2)."""
        import warnings

        from trapper_client import err

        with warnings.catch_warnings():
            warnings.simplefilter("error", err.UnknownFilterWarning)
            total = component.get(page_size=1).pagination.count
            assert component.get(page_size=1, deployment_id="zzz-no-such-deployment").pagination.count == 0
            assert component.get(page_size=1, setup_by="zzz-no-such-person").pagination.count == 0
        with pytest.warns(err.UnknownFilterWarning):
            ignored = component.get(page_size=1, colls=1, ordering="-pk")
        assert ignored.pagination.count == total      # and it really is ignored

    @pytest.mark.e2e
    def test_dates_are_datetimes_in_the_list_and_in_the_export(self, component):
        """The list and the export spell the same instant differently; both are read as aware datetimes."""
        from datetime import datetime

        listed = {d.pk: d for d in component.where(page_size=100)}
        exported = {r.pk: r for r in component.export(file=None)}
        common = [pk for pk in listed if pk in exported and listed[pk].start_date is not None]
        if not common:
            pytest.skip("No deployment with a start date on this server")
        for pk in common:
            for value in (listed[pk].start_date, exported[pk].start_date):
                assert isinstance(value, datetime) and value.tzinfo is not None
            assert listed[pk].start_date == exported[pk].start_date
            assert listed[pk].end_date == exported[pk].end_date

    @pytest.mark.e2e
    def test_in_area_gives_the_deployments_of_the_locations_in_the_area(self, component):
        """``in_area`` agrees with doing it by hand: the locations in the area, then their deployments."""

        everything = list(component.where(page_size=100))
        if not everything:
            pytest.skip("No deployments on this server")
        by_location = {}
        for dep in everything:
            by_location.setdefault(dep.location, []).append(dep.pk)

        locations = LocationsComponent(component.client)
        located = [loc for loc in locations.where(page_size=100) if loc.longitude is not None]
        target = next((loc for loc in located if loc.pk in by_location), None)
        if target is None:
            pytest.skip("No deployment on a location with coordinates")
        lon, lat = target.longitude, target.latitude

        box = (lon - 0.001, lat - 0.001, lon + 0.001, lat + 0.001)
        inside = {l.pk for l in located if box[0] <= l.longitude <= box[2] and box[1] <= l.latitude <= box[3]}
        expected = {pk for loc in inside for pk in by_location.get(loc, [])}
        found = list(component.in_area(bbox=box, page_size=100))
        assert {d.pk for d in found} == expected and expected
        assert {d.location for d in found} <= inside

        around = {d.pk for d in component.in_area(center=(lon, lat), radius=1, page_size=100)}
        assert set(by_location[target.pk]) <= around

        far = (lon + 90 if lon <= 0 else lon - 90, -1.0, lon + 91 if lon <= 0 else lon - 89, 1.0)
        assert not {d.pk for d in component.in_area(bbox=far)} & set(by_location[target.pk])
