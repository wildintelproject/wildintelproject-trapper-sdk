"""
Unit tests for LocationsGeoJsonComponent.

All API calls are mocked — no real server needed.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from trapper_client.components.locations_geojson import LocationsGeoJsonComponent


@pytest.fixture
def client():
    return MagicMock()


@pytest.fixture
def component(client):
    return LocationsGeoJsonComponent(client)


def test_endpoint_matches_server_route():
    """Regresión: el endpoint no tenía el prefijo geomap/ que registra la ruta
    real en el servidor Trapper (geomap/urls.py: ^geomap/ -> ^api/locations/geojson/$),
    lo que provocaba un 404 siempre."""
    assert LocationsGeoJsonComponent.endpoint == "geomap/api/locations/geojson/"


def test_get_uses_component_endpoint(component, client):
    component.get()
    assert client.get.call_args[0][0] == "geomap/api/locations/geojson/"


def test_get_maps_collection_id_to_colls_query_param(component, client):
    component.get(collection_id=3)
    query = client.get.call_args[1]["query"]
    assert query["colls"] == 3


def test_get_passes_extra_kwargs_as_query_params(component, client):
    component.get(search="camera trap")
    query = client.get.call_args[1]["query"]
    assert query["search"] == "camera trap"


@pytest.mark.parametrize(
    "method_name",
    ["get_all", "all", "where", "export"],
)
def test_unsupported_methods_raise_not_implemented(component, method_name):
    with pytest.raises(NotImplementedError):
        getattr(component, method_name)()


def test_find_raises_not_implemented(component):
    with pytest.raises(NotImplementedError):
        component.find(1)
