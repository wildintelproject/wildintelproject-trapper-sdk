# Recursos

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — el mismo código en ambas. Consulta [Versiones de Trapper](versions.md).

`client.resources` — ficheros multimedia individuales (imágenes y vídeos) registrados en un despliegue.

**Endpoints:**

- `GET /storage/api/resources` (listado + detalle)
- `GET /storage/api/resources/collection/{collection_pk}` (limitado a una colección)
- `GET /storage/api/resources/location/{location_pk}` (limitado a una localización)

## Filtros

| Parámetro | Tipo | Descripción |
|---|---|---|
| `pk` | PK separadas por comas | Filtra por PK concretas de recursos |
| `resource_type` | opción | Filtra por tipo de recurso |
| `status` | opción | Filtra por estado del recurso |
| `rdate_from`, `rdate_to` | fecha | Rango de `date_recorded` |
| `udate_from`, `udate_to` | fecha | Rango de `date_uploaded` |
| `rtime_from`, `rtime_to` | HH:MM | Rango de hora del día sobre `date_recorded` |
| `owner` | booleano | `true` = solo recursos propiedad o gestionados por el usuario actual |
| `locations_map` | PK separadas por comas | Filtra mediante `deployment__location` |
| `collections` | lista de PK | Filtra por una o más PK de colección |
| `deployments` | PK repetibles | Filtra por PK de despliegue |
| `deployment__isnull` | booleano | `true` = recursos sin despliegue |
| `tags` | lista de PK | Filtra por PK de etiqueta |
| `observation_type` | cadena | Búsqueda de texto completo de `observation_type:<valor>` |
| `species` | repetible | Búsqueda de texto completo de `species_id:<valor>` |
| `timestamp_error` | booleano | `true` = recursos fuera del rango de fechas del despliegue |
| `search` | cadena | Búsqueda de texto completo en el nombre y los vectores de datos |

## Los seis patrones de acceso

```python
# Iteración perezosa con filtros (all() es lo mismo)
for res in client.resources.where(status="Public", deployments=12):
    print(res)

# Una página
page = client.resources.get(page=1, page_size=100, resource_type="I")

# Un solo elemento
item = client.resources.find(123)

# Exportación a CSV
client.resources.export(file="resources.csv", status="Public")
```

Consulta [Uso](../usage.md) si algo de esto te resulta desconocido: es la misma interfaz en todos los componentes.

## Limitado a una colección o a una localización

Cada patrón de acceso tiene una variante `_by_collection`/`_by_location`, que usa
`/storage/api/resources/collection/{collection_pk}` o `/storage/api/resources/location/{location_pk}`
en lugar del endpoint general:

```python
# Todos los recursos de una colección (perezoso)
for res in client.resources.where_by_collection(collection_pk=5):
    print(res)

page = client.resources.get_by_collection(collection_pk=5, page=2, page_size=25)
result = client.resources.get_all_by_collection(collection_pk=5)
res = client.resources.find_by_collection(collection_pk=5, resource_pk=123)

# Todos los recursos de una localización (perezoso)
for res in client.resources.where_by_location(location_pk=42):
    print(res)

page = client.resources.get_by_location(location_pk=42, page_size=10)
result = client.resources.get_all_by_location(location_pk=42)
res = client.resources.find_by_location(location_pk=42, resource_pk=99)
```

Así es también como se listan los recursos de una [colección](collections.md): `CollectionsComponent`
solo lista *colecciones*, no los recursos que contienen.
