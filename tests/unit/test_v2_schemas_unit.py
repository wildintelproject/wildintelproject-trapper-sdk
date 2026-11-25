"""
Schemas must parse payloads captured from a real Trapper v2 server (2.0.0a).

v2 returns ``null`` for the UI link fields (``*_data``, ``owner_profile``), drops ``status``/``status_ai`` and
``classification``, and wraps user-classification attributes as ``{"value": ...}``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from trapper_client.schemas.classifications import ClassificationProject, Classification
from trapper_client.schemas.classifications_map import ClassificationMap
from trapper_client.schemas.classificators import Classificator
from trapper_client.schemas.ai_classifications import AIClassification, AIObservationAttr
from trapper_client.schemas.user_classifications import UserClassification, UserObservationAttr

PAYLOADS = json.loads((Path(__file__).parent / "data" / "trapper_v2_payloads.json").read_text(encoding="utf-8"))

SCHEMAS = {
    "ai_classifications": AIClassification,
    "classification_projects": ClassificationProject,
    "classification_results": Classification,
    "classifications_map": ClassificationMap,
    "classificators": Classificator,
    "user_classifications": UserClassification,
}


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_real_v2_rows_validate(name):
    for row in PAYLOADS[name]:
        SCHEMAS[name].model_validate(row)


def test_v2_user_classification_attrs_are_unwrapped():
    record = UserClassification.model_validate(PAYLOADS["user_classifications"][0])
    attr = record.dynamic_attrs[0]
    assert isinstance(attr.observation_type, str)
    assert isinstance(attr.count, str)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ({"observation_type": {"value": "animal"}, "species": {"value": "Lynx"}, "count": {"value": "2"}}, ("animal", "Lynx", "2")),
        ({"observation_type": "animal", "species": "Lynx", "count": "2"}, ("animal", "Lynx", "2")),  # v1 shape
    ],
)
def test_attrs_accept_v1_and_v2_shapes(raw, expected):
    a = UserObservationAttr.model_validate(raw)
    assert (a.observation_type, a.species, a.count) == expected


def test_v2_ai_classification_reads_like_v1():
    """v2 has no owner, classification or created_at, and puts the confidence (%) next to the value."""
    record = AIClassification.model_validate(PAYLOADS["ai_classifications"][0])
    assert record.owner is None and record.classification is None and record.created_at is None
    attr = record.dynamic_attrs[0]
    assert attr.observation_type == "animal"
    assert attr.species == "European Rabbit (Oryctolagus cuniculus)"
    assert attr.classification_confidence == "0.93"  # the v1 form: a fraction
    assert record.ai_provider == "DeepFaune Classifier v1.2" and record.bboxes is True


@pytest.mark.parametrize(
    "raw, confidence",
    [
        ({"observation_type": "animal", "species": "Lynx", "classification_confidence": "0.41"}, "0.41"),  # v1
        ({"observation_type": {"value": "animal", "confidence": 41.0}, "species": {"value": "Lynx", "confidence": 41.0}}, "0.41"),
        ({"observation_type": {"value": "animal", "confidence": 90.0}, "species": {"value": "Lynx"}}, "0.90"),
        ({"observation_type": {"value": "blank"}, "species": {"value": "None"}}, None),
    ],
)
def test_ai_confidence_is_a_fraction_on_both_versions(raw, confidence):
    assert AIObservationAttr.model_validate(raw).classification_confidence == confidence


@pytest.mark.parametrize("species", ["None", {"value": "None"}, ""])
def test_missing_species_is_none(species):
    """Trapper writes a missing species as the text ``"None"`` (v1 and v2)."""
    assert UserObservationAttr.model_validate({"observation_type": "blank", "species": species}).species is None


def test_v1_only_fields_are_optional():
    row = dict(PAYLOADS["classification_results"][0])
    row.pop("approved", None)
    record = Classification.model_validate(row)
    assert record.status is None and record.status_ai is None


def test_resource_without_name_validates():
    """The ``/storage/api/resources/location/<pk>`` sub-endpoint omits ``name``."""
    from trapper_client.schemas import Resource

    assert Resource.model_validate({"pk": 29, "resource_type": "I"}).name is None


def test_v2_species_has_class_and_order():
    from trapper_client.schemas import Species

    row = {"pk": 632, "__str__": "Iberian Lynx (Lynx pardinus)", "english_name": "Iberian Lynx",
           "latin_name": "Lynx pardinus", "taxon_class": "Mammalia", "order": "Carnivora", "family": "Felidae",
           "genus": "Lynx"}
    sp = Species.model_validate(row)
    assert sp.display_name == "Iberian Lynx (Lynx pardinus)" and sp.taxon_class == "Mammalia" and sp.order == "Carnivora"


def test_species_unknown_filter_warns():
    from unittest.mock import MagicMock

    from tests.base_component_tests import paginated_response
    from trapper_client import err
    from trapper_client.components.species import SpeciesComponent

    client = MagicMock()
    client.server_version = "v2"
    client.get.return_value = paginated_response([])
    with pytest.warns(err.UnknownFilterWarning, match="ignores 'genus'"):
        SpeciesComponent(client).get(genus="Lynx")


@pytest.mark.parametrize("name", ["search", "username"])
def test_users_have_no_filters(name):
    from unittest.mock import MagicMock

    from tests.base_component_tests import paginated_response
    from trapper_client import err
    from trapper_client.components.users import UsersComponent

    client = MagicMock()
    client.server_version = "v1"
    client.get.return_value = paginated_response([])
    with pytest.warns(err.UnknownFilterWarning, match=f"ignores .{name}.*it applies no filter"):
        UsersComponent(client).get(**{name: "ana"})


def test_research_project_collection_date_is_a_datetime():
    from datetime import datetime

    from trapper_client.schemas import ResearchProjectCollection

    row = {"pk": 4, "collection_pk": 5, "name": "cf collection", "owner": "rp_staff", "owner_profile": None,
           "status": "Private", "date_created": "2026-11-23T23:22:02.934616Z", "description": ""}
    assert isinstance(ResearchProjectCollection.model_validate(row).date_created, datetime)


def test_research_project_collection_filters():
    import warnings
    from unittest.mock import MagicMock

    from tests.base_component_tests import paginated_response
    from trapper_client import err
    from trapper_client.components.research_project_collections import ResearchProjectsCollectionsComponent

    client = MagicMock()
    client.server_version = "v1"
    client.get.return_value = paginated_response([])
    component = ResearchProjectsCollectionsComponent(client)
    with warnings.catch_warnings():
        warnings.simplefilter("error", err.UnknownFilterWarning)
        component.get_project(10, status="Private", owner=True, search="a")
    with pytest.warns(err.UnknownFilterWarning, match="ignores 'name'"):
        component.get_project(10, name="x")


@pytest.mark.parametrize("component, good, bad", [
    ("maps", {"search": "x", "owner": True}, {"name": "x"}),
    ("locations_geojson", {"colls": 2, "in_bbox": "-7,36,-6,38", "radius": "-6,37,5000", "search": "x"}, {"zzz": 1}),
])
def test_v1_map_components_warn_about_ignored_filters(component, good, bad):
    import warnings
    from unittest.mock import MagicMock

    from tests.base_component_tests import paginated_response
    from trapper_client import err
    from trapper_client.components.locations_geojson import LocationsGeoJsonComponent
    from trapper_client.components.maps import MapsComponent

    cls = {"maps": MapsComponent, "locations_geojson": LocationsGeoJsonComponent}[component]
    client = MagicMock()
    client.server_version = "v1"
    row = {"type": "FeatureCollection", "features": []} if component == "locations_geojson" else {"pk": 2}
    client.get.return_value = paginated_response([row])
    with warnings.catch_warnings():
        warnings.simplefilter("error", err.UnknownFilterWarning)
        cls(client).get(**good)
    with pytest.warns(err.UnknownFilterWarning):
        cls(client).get(**bad)
