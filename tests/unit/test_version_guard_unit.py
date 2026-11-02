"""
Components that Trapper v2 removed must fail fast, with a clear error, on a v2 server.

All requests are mocked — no real server is needed.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from trapper_client import err
from trapper_client.components.collections import CollectionsComponent
from trapper_client.components.locations import LocationsComponent
from trapper_client.components.locations_geojson import LocationsGeoJsonComponent
from trapper_client.components.maps import MapsComponent


def client_for(version: str) -> MagicMock:
    client = MagicMock()
    client.server_version = version
    return client


class TestV1OnlyComponentsOnV2:
    @pytest.mark.parametrize("method", ["get", "where", "get_all", "all", "export"])
    def test_maps_reads_are_refused(self, method):
        client = client_for("v2")
        with pytest.raises(err.UnsupportedVersionError, match="MapsComponent.*v1.*runs Trapper v2"):
            getattr(MapsComponent(client), method)()
        client.get.assert_not_called()

    def test_maps_find_is_refused(self):
        with pytest.raises(err.UnsupportedVersionError):
            MapsComponent(client_for("v2")).find(1)

    def test_locations_geojson_is_refused(self):
        client = client_for("v2")
        with pytest.raises(err.UnsupportedVersionError, match="LocationsGeoJsonComponent"):
            LocationsGeoJsonComponent(client).get()
        client.get.assert_not_called()

    @pytest.mark.parametrize(
        "method,args",
        [("where_ondemand", ()), ("get_ondemand", ()), ("get_all_ondemand", ()), ("find_ondemand", (1,))],
    )
    def test_collections_ondemand_is_refused(self, method, args):
        client = client_for("v2")
        with pytest.raises(err.UnsupportedVersionError, match="collections_ondemand"):
            getattr(CollectionsComponent(client), method)(*args)
        client.get.assert_not_called()
        client.get_one.assert_not_called()

    def test_error_is_an_api_error(self):
        assert issubclass(err.UnsupportedVersionError, err.APIError)


class TestVersionNeutralComponentsOnV2:
    def test_locations_do_not_need_to_know_the_version(self):
        """Regular components must not even trigger the version probe."""
        client = MagicMock()
        type(client).server_version = property(lambda self: pytest.fail("version probed"))
        client.get.return_value = {"pagination": {"page": 1, "pages": 1, "count": 0, "per_page": 50}, "results": []}
        LocationsComponent(client).get()

    def test_collections_non_ondemand_methods_work_on_v2(self):
        client = client_for("v2")
        client.get.return_value = {"pagination": {"page": 1, "pages": 1, "count": 0, "per_page": 50}, "results": []}
        CollectionsComponent(client).get()
        client.get.assert_called_once()

    def test_collections_map_and_append_work_on_v2(self):
        assert CollectionsComponent(client_for("v2")).where_map() is not None
        assert CollectionsComponent(client_for("v2")).where_append() is not None


class TestV1OnlyComponentsOnV1:
    def test_maps_work_on_v1(self):
        client = client_for("v1")
        client.get.return_value = {"pagination": {"page": 1, "pages": 1, "count": 0, "per_page": 50}, "results": []}
        MapsComponent(client).get()
        client.get.assert_called_once()


class TestImportsAreV1Only:
    """Trapper v2 no longer exposes the HTML import forms (imports go through the Django admin)."""

    def test_import_locations_refused_on_v2(self, tmp_path):
        from trapper_client.components.locations import LocationsComponent
        client = client_for("v2")
        f = tmp_path / "l.csv"
        f.write_text("a\n")
        with pytest.raises(err.UnsupportedVersionError, match="import_locations"):
            LocationsComponent(client).import_locations(file=f, research_project=1, timezone="UTC")
        client.session_login.assert_not_called()

    def test_import_deployments_refused_on_v2(self, tmp_path):
        from trapper_client.components.deployments import DeploymentsComponent
        client = client_for("v2")
        f = tmp_path / "d.csv"
        f.write_text("a\n")
        with pytest.raises(err.UnsupportedVersionError, match="import_deployments"):
            DeploymentsComponent(client).import_deployments(file=f, timezone="UTC", research_project=1)
        client.session_login.assert_not_called()
