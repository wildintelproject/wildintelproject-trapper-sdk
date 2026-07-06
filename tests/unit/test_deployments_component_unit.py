"""
Unit tests for LocationsComponent.
"""
from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import ComponentUnitTestBase, paginated_response
from trapper_client.api_query import APIQuery
from trapper_client.components.deployments import DeploymentsComponent
from trapper_client.schemas import  Deployment, DeploymentExport

class TestDeploymentsComponent(ComponentUnitTestBase):
    component_class = DeploymentsComponent
    schema = Deployment
    export_schema = DeploymentExport
    find_pk = 1
    valid_item = {"pk": 1, "name": "Deployment A"}
    valid_export_item = {
        "_id": 1,
        "deployment_id": "dona_001",
        "latitude": 37.1,
        "longitude": -6.9,
    }


COLLECTION_ID = 5


# ── by_collection / export_by_collection ──────────────────────────────────────
#
# Regresión: ambos métodos estaban comentados en el código (el `def` deshabilitado,
# dejando solo el docstring como statement huérfano), pese a estar documentados como
# ejemplo de uso en la propia clase y en TrapperClient. Cualquier llamada real a
# client.deployments.by_collection(...) lanzaba AttributeError.

class TestByCollection:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return DeploymentsComponent(client)

    def test_by_collection_returns_api_query(self, component):
        assert isinstance(component.by_collection(COLLECTION_ID), APIQuery)

    def test_by_collection_uses_component_endpoint(self, component):
        query = component.by_collection(COLLECTION_ID)
        assert query.endpoint == DeploymentsComponent.endpoint

    def test_by_collection_maps_collection_id_to_colls_param(self, component):
        query = component.by_collection(COLLECTION_ID)
        assert query.query["colls"] == COLLECTION_ID

    def test_by_collection_passes_extra_kwargs(self, component):
        query = component.by_collection(COLLECTION_ID, status="Public")
        assert query.query["status"] == "Public"

    def test_by_collection_passes_page_size(self, component):
        query = component.by_collection(COLLECTION_ID, page_size=25)
        assert query._page_size == 25


class TestExportByCollection:

    @pytest.fixture
    def client(self):
        return MagicMock()

    @pytest.fixture
    def component(self, client):
        return DeploymentsComponent(client)

    def test_export_by_collection_uses_export_endpoint(self, component, client):
        client.get_all.return_value = paginated_response([])
        component.export_by_collection(COLLECTION_ID, file=None)
        assert client.get_all.call_args[0][0] == DeploymentsComponent.export_endpoint

    def test_export_by_collection_maps_collection_id_to_colls_param(self, component, client):
        client.get_all.return_value = paginated_response([])
        component.export_by_collection(COLLECTION_ID, file=None)
        call_params = client.get_all.call_args[1]["query"]
        assert call_params["colls"] == COLLECTION_ID

    def test_export_by_collection_returns_list_when_file_is_none(self, component, client):
        client.get_all.return_value = paginated_response([{
            "_id": 1, "deployment_id": "dona_001", "latitude": 37.1, "longitude": -6.9,
        }])
        result = component.export_by_collection(COLLECTION_ID, file=None)
        assert isinstance(result, list)
        assert isinstance(result[0], DeploymentExport)