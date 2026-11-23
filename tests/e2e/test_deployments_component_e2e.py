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
from trapper_client import DeploymentsComponent
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
