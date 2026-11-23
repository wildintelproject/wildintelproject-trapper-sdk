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
| `pk` | lista de PK | Filtra por PK concretas de colecciones |
| `status` | opción | `Private`, `OnDemand`, `Public` o `Archived` ([`CollectionStatus`](#filtrar-por-estado)), en cualquier caso |
| `owner` | booleano | `true` = solo colecciones propiedad o gestionadas por el usuario actual |
| `owners` | lista de PK | Filtra por las PK de uno o más propietarios |
| `research_projects` | lista de PK | Filtra por las PK de uno o más proyectos de investigación |
| `locations_map` | lista de PK | Filtra mediante `resources__deployment__location` (**solo v1**: Trapper v2 lo ignora) |
| `search` | cadena | Búsqueda de texto completo en `name` y el nombre de usuario del propietario |

Las listas (`pk`, `owners`, `research_projects`, `locations_map`) se pueden dar como lista o como cadena separada por
comas: `pk=[2, 1]` y `pk="2,1"` son lo mismo. Trapper lee `pk` y `locations_map` como una cadena con comas y `owners` y
`research_projects` como parámetros repetidos, y `pk=[2, 1]` enviado de la otra forma se queda con **un** solo pk; el
SDK envía cada una como Trapper la lee.

### Filtrar por estado

Trapper compara `status` tal como está guardado, distinguiendo mayúsculas, y un valor que no existe es un **resultado
vacío, no un error**: `status="private"` y `status="Bogus"` dan cero colecciones. El SDK lo resuelve con
`CollectionStatus` (`Private`, `OnDemand`, `Public`, `Archived`), aceptando cualquier caso, la etiqueta (`"On demand"`)
o el miembro, y lanza un `ValueError` con los valores válidos antes de cualquier petición si no es ninguno:

```python
from trapper_client import CollectionStatus

client.collections.where(status="public")                    # igual que "Public"
client.collections.where(status=CollectionStatus.ON_DEMAND)
client.collections.where(status="Bogus")                     # ValueError: use one of Private, OnDemand, Public, Archived
```

!!! warning "Un filtro que Trapper no aplica"
    Trapper ignora un parámetro que no es uno de sus filtros **sin dar error**, y la lista vuelve sin filtrar; el SDK
    emite un `UnknownFilterWarning` que lo nombra (la petición se envía igualmente). Además de los de la tabla, la
    lista aplica `name`, `period_begin`, `period_end`, `is_complete_cs_collection`, `cs_deployment`, `managers` y
    `members`. `locations_map` lo ignora v2, y `description`, `date_created` y `ordering` las dos. Para silenciarlo:
    `warnings.simplefilter("ignore", err.UnknownFilterWarning)`.

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
