"""
The new Trapper API (refactor-api-ninja, /api/v2/...): detection, versioned routes, order and slashes (issue #129).

No server needed: httpx.MockTransport stands for one.
"""
from __future__ import annotations

import warnings
from unittest.mock import MagicMock

import httpx
import pytest

from tests.base_component_tests import paginated_response
from trapper_client import err
from trapper_client.components.base import TrapperComponent, versioned
from trapper_client.trapper_client import TrapperClient


def _server(ninja: bool, release: str = "2.0.0a4", calls: list | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request)
        path = request.url.path
        if path == "/api/cs/version/":
            return httpx.Response(200, json={"version": release})
        if path == "/api/v2/probe/auth/":
            return httpx.Response(200) if ninja else httpx.Response(404, text="<html>Not found</html>")
        if path.startswith("/api/v2/") and not path.endswith("/"):
            return httpx.Response(301, headers={"location": path + "/"})
        return httpx.Response(200, json={"pagination": {"page": 1, "pages": 1, "count": 0}, "results": []})
    return handler


def _client(handler, **kw):
    client = TrapperClient(base_url="http://trapper.test", access_token="t", **kw)
    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    return client


class TestDetection:

    def test_auto_finds_the_new_api(self):
        client = _client(_server(ninja=True))
        assert client.server_version == "v2" and client.api_flavor == "ninja"

    def test_auto_on_the_old_v2(self):
        client = _client(_server(ninja=False, release="2.0.0a"))
        assert client.server_version == "v2" and client.api_flavor == "legacy"

    def test_v1_does_not_probe(self):
        calls: list = []
        client = _client(_server(ninja=False, release="v1.7.4", calls=calls))
        assert client.api_flavor == "legacy"
        assert all(c.url.path != "/api/v2/probe/auth/" for c in calls)

    def test_ninja_is_forced_without_requests(self):
        calls: list = []
        client = _client(_server(ninja=False, calls=calls), trapper_version="ninja")
        assert client.server_version == "v2" and client.api_flavor == "ninja" and calls == []

    def test_v2_forces_the_old_api(self):
        calls: list = []
        client = _client(_server(ninja=True, calls=calls), trapper_version="v2")
        assert client.api_flavor == "legacy" and calls == []


class _Things(TrapperComponent):
    endpoint = versioned("old/api/things", ninja="api/v2/things/")
    schema = dict
    known_filters = {"v1": frozenset({"name"}), "v2": frozenset({"name"}), "ninja": frozenset({"name", "deployment"})}


def _mock(flavor):
    client = MagicMock()
    client.server_version = "v2"
    client.api_flavor = flavor
    client.get.return_value = paginated_response([])
    client.get_all.return_value = paginated_response([])
    return client


class TestVersionedRoutes:

    def test_by_flavor(self):
        assert _Things(_mock("ninja")).endpoint == "api/v2/things/"
        assert _Things(_mock("legacy")).endpoint == "old/api/things"

    def test_class_and_mock_client_get_the_old_one(self):
        assert _Things.endpoint == "old/api/things"
        assert _Things(MagicMock()).endpoint == "old/api/things"

    def test_the_lists_of_the_sdk_have_a_ninja_route(self):
        client = TrapperClient(base_url="http://x", access_token="t", trapper_version="ninja")
        routes = {name: getattr(client, name).endpoint for name in (
            "locations", "deployments", "resources", "collections", "research_projects", "classification_projects",
            "classificators", "classification_results", "classifications_map", "user_classifications",
            "ai_classifications", "sequences", "species", "users")}
        assert all(route.startswith("api/v2/") for route in routes.values()), routes


class TestOrderAndParameters:

    @pytest.mark.parametrize("call", ["get", "get_all"])
    def test_sort_by_pk_on_the_new_api(self, call):
        client = _mock("ninja")
        getattr(_Things(client), call)()
        method = client.get if call == "get" else client.get_all
        assert method.call_args[1]["query"]["sort_by"] == "pk"

    def test_where_sorts_by_pk(self):
        assert _Things(_mock("ninja")).where().query["sort_by"] == "pk"

    def test_the_callers_order_is_kept(self):
        client = _mock("ninja")
        _Things(client).get(sort_by="name", reverse=True)
        assert client.get.call_args[1]["query"]["sort_by"] == "name"

    def test_no_sort_by_on_the_old_api(self):
        client = _mock("legacy")
        _Things(client).get()
        assert "sort_by" not in client.get.call_args[1]["query"]

    def test_ninja_filters_and_paging_parameters(self):
        client = _mock("ninja")
        with warnings.catch_warnings():
            warnings.simplefilter("error", err.UnknownFilterWarning)
            _Things(client).get(deployment=3, sort_by="name", reverse=True, all_filtered=False)
        with pytest.warns(err.UnknownFilterWarning):
            _Things(client).get(status=True)


def test_the_new_routes_get_their_trailing_slash():
    calls: list = []
    client = _client(_server(ninja=True, calls=calls), trapper_version="ninja")
    client.get_one("api/v2/locations/1")
    assert calls[-1].url.path == "/api/v2/locations/1/"
