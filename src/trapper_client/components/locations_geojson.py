"""
Component for the /api/locations/geojson/ resource.
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
    Component for the ``/api/locations/geojson/`` resource.

    This endpoint returns a GeoJSON FeatureCollection (not paginated).
    Use :meth:`get` as the primary method. All other inherited methods
    raise ``NotImplementedError``.

    **Available filter fields:**

    In addition to the filters provided for Localizations, the following are added:

    |------------------|-------------|-------------|
    | Parameter        | Type        | Description |
    |------------------|-------------|-------------|
    | locations	       | Location PKs | (alias for locations_map)
    | colls	           | Collection PKs | associated via deployments
    | reses	           | Resource PKs | associated via deployments
    | classes	       | Classification PKs | associated via deployments
    | radius	       | lon,lat,meters |  filters by distance from a point
    | search=          | string        | Searches across: location_id, name, description, county, city, owner__username, deployments__deployment_id
    | in_bbox          | minLon,minLat,maxLon,maxLat |	Filters locations within a geographic bounding box

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

    endpoint = "api/locations/geojson/"
    schema = LocationGeoJsonFeatureCollection

    def get(
        self,
        collection_id: int | None = None,
        query: Dict[str, Any] | None = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Fetch locations as a GeoJSON FeatureCollection.

        Args:
            collection_id: Optional collection ID mapped to ``colls`` query param.
            query: Base query parameters.
            **kwargs: Extra query parameters merged into ``query``.

        Returns:
            GeoJSON payload as a ``dict`` (FeatureCollection).
        """
        q = dict(query or {})
        q.update(kwargs)
        if collection_id is not None:
            q["colls"] = collection_id
        return self.client.get(self.endpoint, query=q)

    def get_all(self, **kwargs) -> None:  # type: ignore[override]
        raise NotImplementedError(_NOT_SUPPORTED)

    def all(self, **kwargs) -> None:  # type: ignore[override]
        raise NotImplementedError(_NOT_SUPPORTED)

    def where(self, **kwargs) -> None:  # type: ignore[override]
        raise NotImplementedError(_NOT_SUPPORTED)

    def find(self, pk, **kwargs) -> None:  # type: ignore[override]
        raise NotImplementedError(_NOT_SUPPORTED)

    def export(self, **kwargs) -> None:  # type: ignore[override]
        raise NotImplementedError(_NOT_SUPPORTED)

    def create(self, body) -> None:  # type: ignore[override]
        raise NotImplementedError(_NOT_SUPPORTED)

    def update(self, pk, body) -> None:  # type: ignore[override]
        raise NotImplementedError(_NOT_SUPPORTED)

    def delete(self, pk) -> None:  # type: ignore[override]
        raise NotImplementedError(_NOT_SUPPORTED)