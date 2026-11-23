# Colecciones

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — salvo los métodos `*_ondemand`, que son **solo v1** (`UnsupportedVersionError` en v2). Consulta [Versiones de Trapper](versions.md).

`client.collections` — colecciones de almacenamiento: grupos de recursos subidos juntos.

**Endpoints:**

- `GET /storage/api/collections` (listado + detalle)
- `GET /storage/api/collections_ondemand` — colecciones bajo demanda del usuario actual
- `GET /storage/api/collections_map` — listado de colecciones para dibujar mapas
- `GET /storage/api/collections_append` — colecciones a las que el usuario puede añadir recursos
- `POST /storage/api/collection/process/` — lanza el procesado de una colección subida por FTP

## Filtros

| Parámetro | Tipo | Descripción |
|---|---|---|
| `pk` | PK separadas por comas | Filtra por PK concretas de colecciones |
| `status` | opción | Filtra por estado de la colección |
| `owner` | booleano | `true` = solo colecciones propiedad o gestionadas por el usuario actual |
| `owners` | lista de PK | Filtra por las PK de uno o más propietarios |
| `research_projects` | lista de PK | Filtra por las PK de uno o más proyectos de investigación |
| `locations_map` | PK separadas por comas | Filtra mediante `resources__deployment__location` |
| `search` | cadena | Búsqueda de texto completo en `name` y el nombre de usuario del propietario |

## Los seis patrones de acceso

```python
# Iteración perezosa (all() es lo mismo)
for col in client.collections.where():
    print(col)
for col in client.collections.where(owner=True):
    print(col)
for col in client.collections.where(research_projects=3):
    print(col)

# Una página
page = client.collections.get(page=1, page_size=25)
print(page.pagination.count)

# Un solo elemento
col = client.collections.find(42)
```

Consulta [Uso](../usage.md) si algo de esto te resulta desconocido: es la misma interfaz en todos los componentes.

!!! note "Recursos dentro de una colección"
    `CollectionsComponent` solo lista *las propias colecciones*; para los recursos de una, usa
    [`client.resources.where_by_collection(collection_pk=...)`](resources.md#limitado-a-una-coleccion-o-a-una-localizacion).

## Subendpoints bajo demanda, de mapa y de añadir

Tres endpoints relacionados tienen exactamente el mismo conjunto `where_*`/`get_*`/`get_all_*`/`find_*`
que el principal, limitados a otro subconjunto de colecciones:

```python
# Colecciones bajo demanda del usuario actual (solo v1)
for col in client.collections.where_ondemand():
    print(col)
page = client.collections.get_ondemand(page_size=25)
result = client.collections.get_all_ondemand()
col = client.collections.find_ondemand(42)

# Colecciones para dibujar mapas
for col in client.collections.where_map():
    print(col)

# Colecciones a las que el usuario puede añadir recursos
for col in client.collections.where_append():
    print(col)
```

## Lanzar el procesado de una colección subida por FTP

```python
client.collections.trigger_collection(
    payload={
        "yaml_file": "package_123.yaml",
        "zip_file": "package_123.zip",
        "remove_zip": False,
    },
)
```
