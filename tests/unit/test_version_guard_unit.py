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


def response(status=302, location="/admin/geomap/location/"):
    r = MagicMock()
    r.status_code = status
    r.headers = {"location": location} if location else {}
    r.text = "<html><body><div class='errorlist'>bad column</div></body></html>"
    return r


class TestImportsOnV2:
    """v2 moved the import forms into the Django admin: same API, other URL, CSRF from the page."""

    @pytest.mark.parametrize(
        "cls_path, call, endpoint",
        [
            ("trapper_client.components.locations.LocationsComponent", "import_locations",
             "admin/geomap/location/import-locations/"),
            ("trapper_client.components.deployments.DeploymentsComponent", "import_deployments",
             "admin/geomap/deployment/import-deployments/"),
        ],
    )
    def test_v2_posts_to_the_admin_form_with_csrf_from_page(self, tmp_path, cls_path, call, endpoint):
        import importlib
        mod, name = cls_path.rsplit(".", 1)
        comp_cls = getattr(importlib.import_module(mod), name)
        client = client_for("v2")
        client.session_post_multipart.return_value = response()
        f = tmp_path / "x.csv"
        f.write_text("a\n")
        kwargs = {"file": f, "research_project": 1, "timezone": "UTC"}
        assert getattr(comp_cls(client), call)(**kwargs) is True
        args, kw = client.session_post_multipart.call_args
        assert args[0] == endpoint
        assert kw["csrf_from_page"] is True
        assert kw["data"]["research_project"] == 1

    def test_v1_keeps_the_old_endpoint_and_call_shape(self, tmp_path):
        client = client_for("v1")
        client.session_post_multipart.return_value = response(location="/geomap/location/")
        f = tmp_path / "x.csv"
        f.write_text("a\n")
        assert LocationsComponent(client).import_locations(file=f, research_project=1, timezone="UTC")
        args, kw = client.session_post_multipart.call_args
        assert args[0] == "geomap/location/import/"
        assert "csrf_from_page" not in kw

    def test_redirect_to_login_is_not_success(self, tmp_path):
        client = client_for("v2")
        client.session_post_multipart.return_value = response(location="/admin/login/?next=/admin/geomap/location/")
        f = tmp_path / "x.csv"
        f.write_text("a\n")
        with pytest.raises(err.APIError, match="import refused.*staff"):
            LocationsComponent(client).import_locations(file=f, research_project=1, timezone="UTC")
        assert LocationsComponent(client).import_locations(
            file=f, research_project=1, timezone="UTC", raise_on_error=False
        ) is False

    def test_form_errors_are_reported(self, tmp_path):
        client = client_for("v2")
        client.session_post_multipart.return_value = response(status=200, location=None)
        client._extract_html_error_text.return_value = "bad column"
        f = tmp_path / "x.csv"
        f.write_text("a\n")
        with pytest.raises(err.APIError, match="bad column"):
            LocationsComponent(client).import_locations(file=f, research_project=1, timezone="UTC")


class TestDeploymentsGeojson:
    """``deployments.geojson()`` replaces maps / locations_geojson, which exist only in v1."""

    FC = {"type": "FeatureCollection", "features": [{"type": "Feature"}]}

    def _client(self, version="v2"):
        client = client_for(version)
        client.get.return_value = {"pagination": {"page": 1, "count": 1}, "results": [self.FC]}
        return client

    def test_refused_on_v1(self):
        from trapper_client.components.deployments import DeploymentsComponent
        client = self._client("v1")
        with pytest.raises(err.UnsupportedVersionError, match="only available in Trapper v2"):
            DeploymentsComponent(client).geojson()
        client.get.assert_not_called()

    def test_returns_the_feature_collection_not_the_envelope(self):
        from trapper_client.components.deployments import DeploymentsComponent
        assert DeploymentsComponent(self._client()).geojson() == self.FC

    def test_filters_become_query_params(self):
        import datetime
        from trapper_client.components.deployments import DeploymentsComponent
        client = self._client()
        DeploymentsComponent(client).geojson(
            classification_project=2, observation_type=["animal", "human"], species=[3, 7],
            start_date_gte=datetime.date(2024, 3, 1), end_date_lte="2024-06-01", refresh=True,
        )
        endpoint = client.get.call_args.args[0]
        q = client.get.call_args.kwargs["query"]
        assert endpoint == "api/deployments/geojson/"
        assert q == {
            "classification_project": 2, "observation_type": "animal,human", "species": "3,7",
            "start_date_gte": "2024-03-01", "end_date_lte": "2024-06-01", "refresh": 1,
        }

    def test_no_filters_sends_an_empty_query(self):
        from trapper_client.components.deployments import DeploymentsComponent
        client = self._client()
        DeploymentsComponent(client).geojson()
        assert client.get.call_args.kwargs["query"] == {}

    def test_locations_geojson_also_unwraps_the_envelope(self):
        client = self._client("v1")
        assert LocationsGeoJsonComponent(client).get() == self.FC

    def test_unwrap_leaves_other_payloads_alone(self):
        from trapper_client.components.base import TrapperComponent
        for data in ({"type": "FeatureCollection", "features": []}, {"results": [1, 2]}, [1], None):
            assert TrapperComponent._unwrap_feature_collection(data) is data
