"""
Single source of truth for every Trapper API endpoint literal used by the client.

Per-component unit tests mostly check *internal* consistency (e.g. "where()
sends component._ondemand_endpoint"), which passes even when that constant
itself points at the wrong resource, is missing an app prefix, or is missing
a trailing slash Django requires. That blind spot is exactly how several real
bugs shipped unnoticed:

- ``ClassificatorsComponent.endpoint`` was missing the ``media_classification/``
  prefix (404 always).
- ``LocationsGeoJsonComponent.endpoint`` was missing the ``geomap/`` prefix.
- ``CollectionsComponent._ondemand_endpoint`` was a copy-paste duplicate of
  ``_append_endpoint``, silently hitting the wrong sub-resource.
- ``ClassificationMediaComponent``, ``ClassificationResultsAggComponent`` and
  ``ClassificationPackageComponent`` were all missing a mandatory trailing
  slash: their Django routes are ``re_path(r"...(?P<project_pk>\\d+)/")``
  without a closing ``$``, but Django's leaf ``URLPattern.resolve()`` still
  requires the regex to consume the *entire* remaining path — any leftover
  characters (including a missing trailing slash) means no match. Since
  ``APIClientBase`` uses a plain ``httpx.Client()`` (``follow_redirects``
  defaults to ``False``), Django's ``APPEND_SLASH`` 301 redirect is never
  followed either, so these calls failed outright.

This file is the registry that would have caught all of the above: every
component that defines ``endpoint``, ``export_endpoint``, or a private
sub-endpoint attribute must have a row here compared against the actual
Django route it targets (cited by app + urls.py pattern). When adding a new
component or endpoint attribute, add a row — ``test_registry_is_exhaustive``
below fails loudly if one is missing.
"""
from __future__ import annotations

import importlib
import pkgutil

import pytest

import trapper_client.components as components_pkg
from trapper_client.components.ai_classifications import AIClassificationsComponent
from trapper_client.components.classification_media import ClassificationMediaComponent
from trapper_client.components.classification_package import ClassificationPackageComponent
from trapper_client.components.classification_projects import ClassificationProjectsComponent
from trapper_client.components.classification_results_agg import ClassificationResultsAggComponent
from trapper_client.components.classifications import ClassificationsComponent
from trapper_client.components.classifications_map import ClassificationsMapComponent
from trapper_client.components.classificators import ClassificatorsComponent
from trapper_client.components.collections import CollectionsComponent
from trapper_client.components.deployments import DeploymentsComponent
from trapper_client.components.locations import LocationsComponent
from trapper_client.components.locations_geojson import LocationsGeoJsonComponent
from trapper_client.components.maps import MapsComponent
from trapper_client.components.sequences import SequencesComponent
from trapper_client.components.users import UsersComponent
from trapper_client.components.research_project_collections import (
    ResearchProjectsCollectionsComponent,
)
from trapper_client.components.research_projects import ResearchProjectsComponent
from trapper_client.components.resources import ResourcesComponent
from trapper_client.components.species import SpeciesComponent
from trapper_client.components.user_classifications import UserClassificationsComponent

# Each row: (component class, attribute name, expected literal value, Django source).
ENDPOINT_REGISTRY: list[tuple[type, str, str, str]] = [
    # ── geomap (mounted at geomap/, trapper/urls.py: re_path(r"^geomap/", ...)) ──
    (LocationsComponent, "endpoint", "/geomap/api/locations",
     "geomap/urls.py: router.register(r'locations', LocationViewSet)"),
    (LocationsComponent, "export_endpoint", "/geomap/api/locations/export/",
     "geomap/urls.py: re_path(r'^api/locations/export/$', LocationTableView)"),
    (LocationsGeoJsonComponent, "endpoint", "geomap/api/locations/geojson/",
     "geomap/urls.py: re_path(r'^api/locations/geojson/$', LocationGeoViewSet)"),
    (DeploymentsComponent, "endpoint", "geomap/api/deployments",
     "geomap/urls.py: router.register(r'deployments', DeploymentViewSet)"),
    (DeploymentsComponent, "export_endpoint", "geomap/api/deployments/export/",
     "geomap/urls.py: re_path(r'^api/deployments/export/$', DeploymentTableView)"),

    # ── storage (mounted at storage/) ─────────────────────────────────────────
    (ResourcesComponent, "endpoint", "storage/api/resources",
     "storage/urls.py: router.register(r'resources', ResourceViewSet)"),
    (CollectionsComponent, "endpoint", "storage/api/collections",
     "storage/urls.py: router.register(r'collections', CollectionViewSet)"),
    (CollectionsComponent, "_ondemand_endpoint", "storage/api/collections_ondemand",
     "storage/urls.py: router.register(r'collections_ondemand', CollectionOnDemandViewSet)"),
    (CollectionsComponent, "_map_endpoint", "storage/api/collections_map",
     "storage/urls.py: router.register(r'collections_map', CollectionMapViewSet)"),
    (CollectionsComponent, "_append_endpoint", "storage/api/collections_append",
     "storage/urls.py: router.register(r'collections_append', CollectionAppendViewSet)"),

    # ── research (mounted at research/) ───────────────────────────────────────
    (ResearchProjectsComponent, "endpoint", "research/api/projects",
     "research/urls.py: router.register(r'projects', ResearchProjectViewSet)"),
    (ResearchProjectsCollectionsComponent, "endpoint",
     "research/api/project/{project_pk}/collections",
     "research/urls.py: router.register(r'project/(?P<project_pk>\\d+)/collections', "
     "ResearchProjectCollectionViewSet)"),

    # ── media_classification (mounted at media_classification/) ──────────────
    (ClassificationProjectsComponent, "endpoint", "/media_classification/api/projects",
     "media_classification/urls.py: router.register(r'projects', ClassificationProjectViewSet)"),
    (ClassificationProjectsComponent, "endpoint_collections",
     "/media_classification/api/project/{project_pk}/collections",
     "media_classification/urls.py: router.register(r'project/(?P<project_pk>\\d+)/collections', "
     "ClassificationProjectCollectionViewSet)"),
    (ClassificationProjectsComponent, "endpoint_resources",
     "media_classification/api/collection/{collection_pk}/resources/",
     "media_classification/urls.py: router.register(r'collection/(?P<collection_pk>\\d+)/resources/$', "
     "ClassificationResourcesViewSet) — trailing slash is mandatory"),
    (ClassificationsComponent, "endpoint", "/media_classification/api/classifications",
     "media_classification/urls.py: router.register(r'classifications', ClassificationViewSet)"),
    (ClassificationsComponent, "export_endpoint",
     "/media_classification/api/classifications/results/{project_pk}/",
     "media_classification/urls.py: re_path(r'^api/classifications/results/(?P<project_pk>\\d+)/', "
     "ClassificationResultsView)"),
    (AIClassificationsComponent, "endpoint", "/media_classification/api/ai-classifications",
     "media_classification/urls.py: router.register(r'ai-classifications', AIClassificationViewSet)"),
    (AIClassificationsComponent, "export_endpoint",
     "/media_classification/api/ai-classifications/results/{project_pk}/",
     "media_classification/urls.py: re_path(r'^api/ai-classifications/results/(?P<project_pk>\\d+)/', "
     "AIClassificationResultsView)"),
    (UserClassificationsComponent, "endpoint", "/media_classification/api/user-classifications",
     "media_classification/urls.py: router.register(r'user-classifications', UserClassificationViewSet)"),
    (ClassificationsMapComponent, "endpoint", "/media_classification/api/classifications_map",
     "media_classification/urls.py: router.register(r'classifications_map', ClassificationMapViewSet)"),
    (ClassificatorsComponent, "endpoint", "/media_classification/api/classificators",
     "media_classification/urls.py: router.register(r'classificators', ClassificatorViewSet)"),
    (ClassificationMediaComponent, "endpoint", "media_classification/api/media/{project_pk}/",
     "media_classification/urls.py: re_path(r'^api/media/(?P<project_pk>\\d+)/', "
     "ClassificationProjectMediaTableView) — trailing slash is mandatory"),
    (ClassificationResultsAggComponent, "endpoint",
     "media_classification/api/classifications/results/agg/{project_pk}/",
     "media_classification/urls.py: re_path(r'^api/classifications/results/agg/(?P<project_pk>\\d+)/', "
     "ClassificationResultsAggView) — trailing slash is mandatory"),
    (ClassificationPackageComponent, "endpoint", "media_classification/api/package/{project_pk}/",
     "media_classification/urls.py: re_path(r'^api/package/(?P<project_pk>\\d+)/', "
     "ResultsDataPackageAPIView) — trailing slash is mandatory"),

    # ── extra_tables (mounted at tables/) ─────────────────────────────────────
    (SpeciesComponent, "endpoint", "tables/api/species",
     "extra_tables/urls.py: router.register(r'species', SpeciesViewSet)"),

    # ── geomap: maps (mounted at geomap/) ──────────────────────────────────────
    (MapsComponent, "endpoint", "geomap/api/maps",
     "geomap/urls.py: router.register(r'maps', MapViewSet)"),

    # ── media_classification: sequences ───────────────────────────────────────
    (SequencesComponent, "endpoint", "media_classification/api/sequences",
     "media_classification/urls.py: router.register(r'sequences', SequenceViewSet)"),

    # ── accounts (mounted at accounts/) ───────────────────────────────────────
    (UsersComponent, "endpoint", "accounts/api/users",
     "accounts/urls.py: router.register(r'users', UserViewSet)"),
]

_ENDPOINT_ATTR_NAMES = {
    "endpoint",
    "export_endpoint",
    "endpoint_collections",
    "endpoint_resources",
    "_ondemand_endpoint",
    "_map_endpoint",
    "_append_endpoint",
}


@pytest.mark.parametrize(
    "component_class, attr_name, expected, source",
    ENDPOINT_REGISTRY,
    ids=[f"{cls.__name__}.{attr}" for cls, attr, _, _ in ENDPOINT_REGISTRY],
)
def test_endpoint_matches_django_route(component_class, attr_name, expected, source):
    """Every endpoint literal must match the real Trapper Django route it targets."""
    actual = getattr(component_class, attr_name)
    assert actual == expected, (
        f"{component_class.__name__}.{attr_name} = {actual!r}, expected {expected!r} "
        f"(server route: {source})"
    )


def test_registry_is_exhaustive():
    """Fail loudly if a component defines an endpoint attribute this registry
    doesn't know about, so a newly added component can't silently skip
    verification against the real Trapper routes."""
    covered = {(cls, attr) for cls, attr, _, _ in ENDPOINT_REGISTRY}

    missing = []
    for _, module_name, _ in pkgutil.iter_modules(components_pkg.__path__):
        # "base" defines no endpoints of its own. "http_uploader" is not a
        # TrapperComponent/endpoint-based class at all (it's the optional,
        # resumable chunked uploader) and its module-level `import aiofiles`/
        # `import blake3` are only guaranteed by the optional "upload" extra,
        # not by the base dependency set this test suite otherwise relies on.
        if module_name in {"base", "http_uploader"}:
            continue
        module = importlib.import_module(f"trapper_client.components.{module_name}")
        for name in dir(module):
            obj = getattr(module, name)
            if not isinstance(obj, type) or obj.__module__ != module.__name__:
                continue
            for attr in _ENDPOINT_ATTR_NAMES:
                if attr in vars(obj) and (obj, attr) not in covered:
                    missing.append(f"{obj.__name__}.{attr}")

    assert not missing, (
        "Endpoint attributes not covered by ENDPOINT_REGISTRY in this file: "
        f"{sorted(missing)}. Add a row pointing at the real Django route."
    )
