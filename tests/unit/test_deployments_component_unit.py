"""
Unit tests for LocationsComponent.
"""
from tests.base_component_tests import ComponentUnitTestBase
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