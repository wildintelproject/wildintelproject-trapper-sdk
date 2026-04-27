"""
Integration tests for LocationsComponent.

Tests the full stack: LocationsComponent → APIClientBase → httpx transport (mocked).
No real network calls — httpx.Client.request is intercepted at the transport level.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from trapper_client.api_client_base import APIClientBase
from trapper_client.components.locations import LocationsComponent
from trapper_client.schemas import Location, LocationExport, PaginatedResult


BASE_URL = "https://trapper.test"
TOKEN = "test-token"

LOCATION_1 = {
    "pk": 10,
    "name": "Sierra Norte",
    "location_id": "SN-001",
    "country": "ES",
    "is_public": True,
}

LOCATION_2 = {
    "pk": 11,
    "name": "Doñana",
    "location_id": "DN-001",
    "country": "ES",
    "is_public": False,
}

EXPORT_ITEM = {
    "_id": 10,
    "locationID": "SN-001",
    "latitude": 37.91,
    "longitude": -5.82,
    "country": "ES",
    "researchProject": "3",
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _json_response(data: dict, status: int = 200) -> httpx.Response:
    content = json.dumps(data).encode()
    return httpx.Response(
        status_code=status,
        headers={"Content-Type": "application/json"},
        content=content,
    )


def _paginated(
    results: list[dict],
    page: int = 1,
    pages: int = 1,
    count: int | None = None,
) -> dict:
    return {
        "pagination": {
            "page": page,
            "pages": pages,
            "page_size": len(results),
            "count": count if count is not None else len(results),
        },
        "results": results,
    }


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClientBase(access_token=TOKEN, base_url=BASE_URL, verify_ssl=False)


@pytest.fixture
def component(api_client):
    return LocationsComponent(api_client)


# ── tests ─────────────────────────────────────────────────────────────────────

class TestLocationsComponentIntegration:

    # ── get: URL y parámetros ─────────────────────────────────────────────────

    def test_get_builds_correct_url(self, component, api_client):
        with patch.object(api_client._client, "request") as mock_req:
            mock_req.return_value = _json_response(_paginated([LOCATION_1]))
            component.get(page_size=10)

        url = mock_req.call_args.kwargs["url"]
        assert BASE_URL in url
        assert "geomap/api/locations" in url

    def test_get_sends_page_and_page_size_as_query_params(self, component, api_client):
        with patch.object(api_client._client, "request") as mock_req:
            mock_req.return_value = _json_response(_paginated([LOCATION_1]))
            component.get(page=2, page_size=5)

        params = mock_req.call_args.kwargs["params"]
        assert params["page"] == 2
        assert params["page_size"] == 5

    def test_get_sends_filter_kwargs_as_query_params(self, component, api_client):
        with patch.object(api_client._client, "request") as mock_req:
            mock_req.return_value = _json_response(_paginated([LOCATION_1]))
            component.get(page_size=10, search="Sierra", owner=True)

        params = mock_req.call_args.kwargs["params"]
        assert params["search"] == "Sierra"
        assert params["owner"] is True

    def test_get_sends_auth_token_header(self, component, api_client):
        with patch.object(api_client._client, "request") as mock_req:
            mock_req.return_value = _json_response(_paginated([LOCATION_1]))
            component.get(page_size=5)

        headers = mock_req.call_args.kwargs["headers"]
        assert headers.get("Authorization") == f"Token {TOKEN}"

    # ── get: parseo de respuesta ──────────────────────────────────────────────

    def test_get_returns_paginated_result(self, component, api_client):
        with patch.object(api_client._client, "request") as mock_req:
            mock_req.return_value = _json_response(_paginated([LOCATION_1, LOCATION_2]))
            result = component.get(page_size=10)

        assert isinstance(result, PaginatedResult)
        assert len(result.results) == 2

    def test_get_results_are_location_instances(self, component, api_client):
        with patch.object(api_client._client, "request") as mock_req:
            mock_req.return_value = _json_response(_paginated([LOCATION_1, LOCATION_2]))
            result = component.get(page_size=10)

        assert all(isinstance(loc, Location) for loc in result.results)

    def test_get_parses_location_fields_correctly(self, component, api_client):
        with patch.object(api_client._client, "request") as mock_req:
            mock_req.return_value = _json_response(_paginated([LOCATION_1]))
            result = component.get(page_size=10)

        loc = result.results[0]
        assert loc.pk == 10
        assert loc.name == "Sierra Norte"
        assert loc.location_id == "SN-001"
        assert loc.country == "ES"
        assert loc.is_public is True

    def test_get_pagination_metadata_is_normalized(self, component, api_client):
        with patch.object(api_client._client, "request") as mock_req:
            mock_req.return_value = _json_response(_paginated([LOCATION_1], page=2, pages=5, count=50))
            result = component.get(page=2, page_size=10)

        assert result.pagination.page == 2
        assert result.pagination.pages == 5
        assert result.pagination.count == 50

    # ── get_all: paginación múltiple ──────────────────────────────────────────

    def test_get_all_fetches_all_pages(self, component, api_client):
        page1 = _paginated([LOCATION_1], page=1, pages=2, count=2)
        page2 = _paginated([LOCATION_2], page=2, pages=2, count=2)

        with patch.object(api_client._client, "request", side_effect=[
            _json_response(page1), _json_response(page2)
        ]):
            result = component.get_all(page_size=1)

        assert len(result.results) == 2
        assert result.results[0].pk == 10
        assert result.results[1].pk == 11

    def test_get_all_no_duplicate_pks_across_pages(self, component, api_client):
        page1 = _paginated([LOCATION_1], page=1, pages=2, count=2)
        page2 = _paginated([LOCATION_2], page=2, pages=2, count=2)

        with patch.object(api_client._client, "request", side_effect=[
            _json_response(page1), _json_response(page2)
        ]):
            result = component.get_all(page_size=1)

        pks = [item.pk for item in result.results]
        assert len(pks) == len(set(pks))

    def test_get_all_single_page_makes_one_request(self, component, api_client):
        with patch.object(api_client._client, "request") as mock_req:
            mock_req.return_value = _json_response(_paginated([LOCATION_1, LOCATION_2]))
            component.get_all(page_size=50)

        assert mock_req.call_count == 1

    # ── find ──────────────────────────────────────────────────────────────────

    def test_find_appends_pk_to_endpoint_url(self, component, api_client):
        with patch.object(api_client._client, "request") as mock_req:
            mock_req.return_value = _json_response(LOCATION_1)
            component.find(10)

        url = mock_req.call_args.kwargs["url"]
        assert "/10" in url
        assert "geomap/api/locations" in url

    def test_find_returns_location_instance(self, component, api_client):
        with patch.object(api_client._client, "request") as mock_req:
            mock_req.return_value = _json_response(LOCATION_1)
            result = component.find(10)

        assert isinstance(result, Location)
        assert result.pk == 10
        assert result.name == "Sierra Norte"

    def test_find_raises_on_404(self, component, api_client):
        with patch.object(api_client._client, "request") as mock_req:
            mock_req.return_value = _json_response(
                {"_error": {"message": "Not found"}}, status=404
            )
            with pytest.raises(Exception):
                component.find(999)

    def test_find_handles_paginated_response_from_server(self, component, api_client):
        """Some Trapper endpoints wrap single items in a paginated envelope."""
        with patch.object(api_client._client, "request") as mock_req:
            mock_req.return_value = _json_response(_paginated([LOCATION_1]))
            result = component.find(10)

        assert isinstance(result, Location)
        assert result.pk == 10

    # ── export ────────────────────────────────────────────────────────────────

    def test_export_uses_export_endpoint_not_list_endpoint(self, component, api_client):
        with patch.object(api_client._client, "request") as mock_req:
            mock_req.return_value = _json_response(_paginated([EXPORT_ITEM]))
            component.export(file=None)

        url = mock_req.call_args.kwargs["url"]
        assert "export" in url

    def test_export_returns_list_of_location_export(self, component, api_client):
        with patch.object(api_client._client, "request") as mock_req:
            mock_req.return_value = _json_response(_paginated([EXPORT_ITEM]))
            result = component.export(file=None)

        assert isinstance(result, list)
        assert isinstance(result[0], LocationExport)

    def test_export_parses_aliased_fields(self, component, api_client):
        with patch.object(api_client._client, "request") as mock_req:
            mock_req.return_value = _json_response(_paginated([EXPORT_ITEM]))
            result = component.export(file=None)

        loc = result[0]
        assert loc.pk == 10          # alias: _id
        assert loc.location_id == "SN-001"  # alias: locationID
        assert loc.latitude == 37.91
        assert loc.longitude == -5.82
        assert loc.research_project_id == 3  # parsed from string "3"

    def test_export_writes_csv_file(self, component, api_client, tmp_path):
        with patch.object(api_client._client, "request") as mock_req:
            mock_req.return_value = _json_response(_paginated([EXPORT_ITEM]))
            out = tmp_path / "locations.csv"
            result = component.export(file=out)

        assert isinstance(result, Path)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_export_csv_contains_data(self, component, api_client, tmp_path):
        with patch.object(api_client._client, "request") as mock_req:
            mock_req.return_value = _json_response(_paginated([EXPORT_ITEM]))
            out = tmp_path / "locations.csv"
            component.export(file=out)

        content = out.read_text(encoding="utf-8")
        assert "SN-001" in content