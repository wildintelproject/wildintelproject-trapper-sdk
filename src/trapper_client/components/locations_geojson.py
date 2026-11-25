"""
Component for the /geomap/api/locations/geojson/ resource.
"""

from __future__ import annotations

from typing import Any, Dict

from trapper_client.api_query import APIQuery
from trapper_client.components.base import TrapperComponent
from trapper_client.schemas import LocationGeoJsonFeatureCollection

_NOT_SUPPORTED = (
    "LocationsGeoJsonComponent only supports .get(). "
    "This endpoint returns a single GeoJSON FeatureCollection, not a paginated list."
)


class LocationsGeoJsonComponent(TrapperComponent[LocationGeoJsonFeatureCollection]):
    """
    Component for the ``/geomap/api/locations/geojson/`` resource.

    This endpoint returns a GeoJSON FeatureCollection (not paginated).
    Use :meth:`get` as the primary method. All other inherited methods
    raise ``NotImplementedError``.

    **Filters** (``LocationGeoFilter``; Trapper ignores any other without an error, the SDK emits an
    ``UnknownFilterWarning``): those of the location list (``owner``, ``owners``, ``research_project``,
    ``research_projects_member``, ``locations_map``, ``location_id``, ``name``, ``city``, ``county``, ``state``,
    ``country``, ``is_public``, ...) and:

    | Parameter | Type | Description |
    |---|---|---|
    | locations | list of PKs | Location PKs (like ``locations_map``) |
    | colls | list of PKs | Collections, through the deployments (``collection_id=`` sets it) |
    | reses | list of PKs | Resources, through the deployments |
    | classes | list of PKs | Classifications, through the deployments |
    | deployments | list of PKs | Deployments |
    | radius | ``lon,lat,meters`` | Within that distance of a point |
    | in_bbox | ``minLon,minLat,maxLon,maxLat`` | Inside a bounding box |
    | search | string | ``location_id``, ``name``, ``description``, ``county``, ``city``, owner's username, ``deployment_id`` |

    **Example:**

    Fetch all locations as GeoJSON::

        geojson = client.locations_geojson.get()
        print(geojson["type"])           # "FeatureCollection"
        print(len(geojson["features"]))  # number of locations

    Filter by collection ID::

        geojson = client.locations_geojson.get(collection_id=3)

    Filter by research project::

        geojson = client.locations_geojson.get(research_project=5)

    Text search::

        geojson = client.locations_geojson.get(search="camera trap")

    Filter by bounding box (minLon, minLat, maxLon, maxLat)::

        geojson = client.locations_geojson.get(in_bbox="-6.0,36.0,0.0,44.0")

    Filter by radius (lon, lat, meters)::

        geojson = client.locations_geojson.get(radius="-5.5,37.3,10000")

    Access feature properties::

        geojson = client.locations_geojson.get(owner=True)
        for feature in geojson["features"]:
            props = feature["properties"]
            coords = feature["geometry"]["coordinates"]
            print(f"{props['name']} → lon={coords[0]}, lat={coords[1]}")

    Combine multiple filters::

        geojson = client.locations_geojson.get(
            research_project=2,
            search="river",
            in_bbox="-6.0,36.0,0.0,44.0",
        )

    """

    endpoint = "geomap/api/locations/geojson/"
    schema = LocationGeoJsonFeatureCollection
    supported_versions = ("v1",)  # removed in Trapper v2
    known_filters = {"v1": frozenset({
        "city", "classes", "colls", "coordinate_uncertainty", "country", "county", "date_created", "deployments",
        "description", "ignore_DST", "is_public", "location_id", "locations", "locations_map", "managers", "name",
        "owner", "owners", "pk", "radius", "research_project", "research_projects_member", "reses", "state",
        "search", "in_bbox",
    })}

    def get(
        self,
        collection_id: int | None = None,
        query: Dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Fetch locations as a GeoJSON FeatureCollection.

        Args:
            collection_id: Optional collection ID mapped to ``colls`` query param.
            query: Base query parameters.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            GeoJSON payload as a ``dict`` (FeatureCollection).
        """
        self._ensure_supported()
        if collection_id is not None:
            kwargs = {**kwargs, "colls": collection_id}
        q = self._merge_query(query, kwargs)
        return self._unwrap_feature_collection(self.client.get(self.endpoint, query=q))

    def get_all(self, **kwargs: Any) -> None:  # type: ignore[override]
        raise NotImplementedError(_NOT_SUPPORTED)

    def all(self, **kwargs: Any) -> None:  # type: ignore[override]
        raise NotImplementedError(_NOT_SUPPORTED)

    def where(self, **kwargs: Any) -> None:  # type: ignore[override]
        raise NotImplementedError(_NOT_SUPPORTED)

    def find(self, pk, **kwargs: Any) -> None:  # type: ignore[override]
        raise NotImplementedError(_NOT_SUPPORTED)

    def export(self, **kwargs: Any) -> None:  # type: ignore[override]
        raise NotImplementedError(_NOT_SUPPORTED)

    def create(self, body) -> None:  # type: ignore[override]
        raise NotImplementedError(_NOT_SUPPORTED)

    def update(self, pk, body) -> None:  # type: ignore[override]
        raise NotImplementedError(_NOT_SUPPORTED)

    def delete(self, pk) -> None:  # type: ignore[override]
        raise NotImplementedError(_NOT_SUPPORTED)