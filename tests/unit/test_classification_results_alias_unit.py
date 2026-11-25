"""``ClassificationResultsComponent`` is the same class as ``ClassificationsComponent``."""
from __future__ import annotations

import trapper_client
from trapper_client import TrapperClient
from trapper_client import components
from trapper_client.components import ClassificationResultsComponent, ClassificationsComponent
from trapper_client.components.classifications import ClassificationResultsComponent as FromModule


def test_the_alias_is_the_same_class():
    assert ClassificationResultsComponent is ClassificationsComponent
    assert FromModule is ClassificationsComponent
    assert "ClassificationResultsComponent" in components.__all__ and "ClassificationsComponent" in components.__all__


def test_the_client_attribute_is_an_instance_of_both():
    client = TrapperClient(base_url="http://localhost:1", access_token="x")
    assert isinstance(client.classification_results, ClassificationResultsComponent)
    assert isinstance(client.classification_results, ClassificationsComponent)
