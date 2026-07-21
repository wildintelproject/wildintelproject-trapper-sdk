# Locations GeoJSON

`client.locations_geojson` — locations as a single GeoJSON `FeatureCollection`, for map rendering.

**Endpoint:** `GET /geomap/api/locations/geojson/`.

## This component only supports `get()`

Unlike every other component, this endpoint returns one GeoJSON document — not a paginated list —
so `get_all()`, `where()`, `all()`, `find()`, and `export()` all raise `NotImplementedError`. Use
`get()` directly:

```python
geojson = client.locations_geojson.get()
print(geojson["type"])           # "FeatureCollection"
print(len(geojson["features"]))  # number of locations
```

## Filters

In addition to the [locations filters](locations.md#filters), this endpoint adds:

| Parameter | Type | Description |
|---|---|---|
| `locations` | Location PKs | Alias for `locations_map` |
| `colls` | Collection PKs | Filter by collections associated via deployments |
| `reses` | Resource PKs | Filter by resources associated via deployments |
| `classes` | Classification PKs | Filter by classifications associated via deployments |
| `radius` | `lon,lat,meters` | Filter by distance from a point |
| `search` | string | Searches `location_id`, `name`, `description`, `county`, `city`, owner username, `deployments__deployment_id` |
| `in_bbox` | `minLon,minLat,maxLon,maxLat` | Filter locations within a geographic bounding box |

## Examples

```python
# Filter by collection ID
geojson = client.locations_geojson.get(collection_id=3)

# Filter by research project
geojson = client.locations_geojson.get(research_project=5)

# Text search
geojson = client.locations_geojson.get(search="camera trap")

# Bounding box (minLon, minLat, maxLon, maxLat)
geojson = client.locations_geojson.get(in_bbox="-6.0,36.0,0.0,44.0")

# Radius (lon, lat, meters)
geojson = client.locations_geojson.get(radius="-5.5,37.3,10000")

# Combine filters
geojson = client.locations_geojson.get(
    research_project=2,
    search="river",
    in_bbox="-6.0,36.0,0.0,44.0",
)

# Access feature properties
geojson = client.locations_geojson.get(owner=True)
for feature in geojson["features"]:
    props = feature["properties"]
    coords = feature["geometry"]["coordinates"]
    print(f"{props['name']} → lon={coords[0]}, lat={coords[1]}")
```
