# Localizaciones GeoJSON

!!! warning "Solo Trapper v1"
    Eliminado en Trapper v2: en un servidor v2 lanza `UnsupportedVersionError`. Usa [`deployments.geojson()`](deployments.md#geojson-solo-trapper-v2). Consulta [Versiones de Trapper](versions.md).

`client.locations_geojson` — las localizaciones como un único `FeatureCollection` GeoJSON, para dibujar mapas.

**Endpoint:** `GET /geomap/api/locations/geojson/`.

## Este componente solo admite `get()`

A diferencia de los demás componentes, este endpoint devuelve un único documento GeoJSON, no una lista
paginada, así que `get_all()`, `where()`, `all()`, `find()` y `export()` lanzan todos
`NotImplementedError`. Usa `get()` directamente:

```python
geojson = client.locations_geojson.get()
print(geojson["type"])           # "FeatureCollection"
print(len(geojson["features"]))  # número de localizaciones
```

## Filtros

Además de los [filtros de localizaciones](locations.md#filtros), este endpoint añade:

| Parámetro | Tipo | Descripción |
|---|---|---|
| `locations` | PK de localizaciones | Alias de `locations_map` |
| `colls` | PK de colecciones | Filtra por colecciones asociadas mediante despliegues |
| `reses` | PK de recursos | Filtra por recursos asociados mediante despliegues |
| `classes` | PK de clasificaciones | Filtra por clasificaciones asociadas mediante despliegues |
| `radius` | `lon,lat,metros` | Filtra por distancia a un punto |
| `search` | cadena | Busca en `location_id`, `name`, `description`, `county`, `city`, nombre de usuario del propietario y `deployments__deployment_id` |
| `in_bbox` | `minLon,minLat,maxLon,maxLat` | Filtra las localizaciones dentro de una caja geográfica |

## Ejemplos

```python
# Filtrar por ID de colección
geojson = client.locations_geojson.get(collection_id=3)

# Filtrar por proyecto de investigación
geojson = client.locations_geojson.get(research_project=5)

# Búsqueda de texto
geojson = client.locations_geojson.get(search="camera trap")

# Caja delimitadora (minLon, minLat, maxLon, maxLat)
geojson = client.locations_geojson.get(in_bbox="-6.0,36.0,0.0,44.0")

# Radio (lon, lat, metros)
geojson = client.locations_geojson.get(radius="-5.5,37.3,10000")

# Combinar filtros
geojson = client.locations_geojson.get(
    research_project=2,
    search="river",
    in_bbox="-6.0,36.0,0.0,44.0",
)

# Acceder a las propiedades de cada elemento
geojson = client.locations_geojson.get(owner=True)
for feature in geojson["features"]:
    props = feature["properties"]
    coords = feature["geometry"]["coordinates"]
    print(f"{props['name']} → lon={coords[0]}, lat={coords[1]}")
```
