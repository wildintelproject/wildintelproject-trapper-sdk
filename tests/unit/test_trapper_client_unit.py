"""
Unit tests for TrapperClient component wiring.

These instantiate the real TrapperClient (no HTTP calls happen at
construction time) instead of mocking components in isolation, so a broken
wiring in `_init_components` (undefined/mismatched component class) is
caught here even though every other component test bypasses TrapperClient
entirely.
"""
from __future__ import annotations

import pytest

import trapper_client
from trapper_client import TrapperClient
import trapper_client.components as components_pkg
import trapper_client.schemas as schemas_pkg
from trapper_client.components import (
    AIClassificationsComponent,
    ClassificationMediaComponent,
    ClassificationPackageComponent,
    ClassificationProjectsComponent,
    ClassificationResultsAggComponent,
    ClassificationsComponent,
    ClassificationsMapComponent,
    ClassificatorsComponent,
    CollectionsComponent,
    DeploymentsComponent,
    LocationsComponent,
    LocationsGeoJsonComponent,
    MapsComponent,
    ResearchProjectsComponent,
    ResourcesComponent,
    SequencesComponent,
    SpeciesComponent,
    UserClassificationsComponent,
    UsersComponent,
)


@pytest.fixture
def client() -> TrapperClient:
    return TrapperClient(access_token="dummy-token", base_url="https://example.com")


def test_trapper_client_instantiates_without_error():
    """TrapperClient() must not raise at construction time.

    Regression test: `_init_components` used to reference
    `ClassificationResultsComponent`, a name that was never imported or
    defined anywhere, which raised NameError on every instantiation.
    """
    TrapperClient(access_token="dummy-token", base_url="https://example.com")


@pytest.mark.parametrize(
    ("attr_name", "expected_type"),
    [
        ("locations", LocationsComponent),
        ("locations_geojson", LocationsGeoJsonComponent),
        ("deployments", DeploymentsComponent),
        ("resources", ResourcesComponent),
        ("collections", CollectionsComponent),
        ("research_projects", ResearchProjectsComponent),
        ("classification_projects", ClassificationProjectsComponent),
        ("classification_media", ClassificationMediaComponent),
        ("classification_results", ClassificationsComponent),
        ("classification_results_agg", ClassificationResultsAggComponent),
        ("classification_package", ClassificationPackageComponent),
        ("ai_classifications", AIClassificationsComponent),
        ("user_classifications", UserClassificationsComponent),
        ("classifications_map", ClassificationsMapComponent),
        ("classificators", ClassificatorsComponent),
        ("species", SpeciesComponent),
        ("maps", MapsComponent),
        ("sequences", SequencesComponent),
        ("users", UsersComponent),
    ],
)
def test_component_attribute_has_expected_type(client, attr_name, expected_type):
    """Every documented `client.<attr>` must be wired to its real component class."""
    assert isinstance(getattr(client, attr_name), expected_type)


def test_top_level_package_reexports_every_component_and_schema():
    """The root `trapper_client/__init__.py` must re-export everything

    `components/__init__.py` and `schemas/__init__.py` expose.

    Regression test: this file used to hand-list re-exports and only ever
    covered the first ~7 components added to the project, silently falling
    behind every time a new component/schema was added afterwards.
    """
    missing_from_namespace = [
        name
        for name in {*components_pkg.__all__, *schemas_pkg.__all__}
        if not hasattr(trapper_client, name)
    ]
    assert not missing_from_namespace, (
        f"Not importable from `trapper_client` directly: {sorted(missing_from_namespace)}"
    )

    missing_from_all = [
        name
        for name in {*components_pkg.__all__, *schemas_pkg.__all__}
        if name not in trapper_client.__all__
    ]
    assert not missing_from_all, (
        f"Present but missing from `trapper_client.__all__`: {sorted(missing_from_all)}"
    )
