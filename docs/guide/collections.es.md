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

Qué da cada una (comprobado en Trapper v1 y v2):

| Método | Campos | Paginación | v2 |
|---|---|---|---|
| principal (`where()`, `get()`, ...) | los nueve de `Collection` | paginada | sí |
| `*_ondemand` | los mismos nueve | paginada | **no**: `UnsupportedVersionError` (Trapper contesta `404`) |
| `*_map` | los mismos nueve | **ninguna**: Trapper devuelve una lista plana e ignora `page_size` | sí |
| `*_append` | solo `pk` y `name` (los demás campos son `None`) | **ninguna**: una lista plana | sí |

El SDK envuelve una lista plana como una sola página, así que `get_map()` y `get_all_append()` funcionan como las
demás y `pagination.count` es la longitud de la lista. `delete_data`, `update_data`, `detail_data` y `owner_profile` son
URLs de la página web en v1 y `None` en v2.

## Crear una colección desde un paquete

Una colección con sus resources se crea desde un **paquete**: un ZIP con los ficheros y un YAML que los describe. El
SDK tiene los dos pasos, y nada más crea una colección con datos: `get_uploader()` deja los dos ficheros en la carpeta
`collections/` de la cuenta en el servidor, y `trigger_collection()` hace que Trapper los procese.

```python
from pathlib import Path

uploader = client.get_uploader()                       # por trozos en v1, reanudable (tus) en v2
uploader.upload(Path("package.yaml"), "collections/package.yaml")
uploader.upload(Path("package.zip"), "collections/package.zip")

response = client.collections.trigger_collection({"yaml_file": "package.yaml", "zip_file": "package.zip"})
print(response.json()["data"]["task_id"])              # la tarea ha empezado: la colección aún no está

# espera: la colección y sus resources aparecen unos segundos después
import time
while not (found := list(client.collections.where(search="Mi colección"))):
    time.sleep(3)
```

El YAML (Trapper lo valida con `collection_schema.yaml`; un problema es un `BadRequestError` con el detalle en
`data.errors`):

```yaml
collections:
  - name: Mi colección               # se reutiliza si la cuenta ya tiene una con este nombre (en el código de Trapper)
    resources_dir: res               # la carpeta del ZIP con una carpeta por deployment
    project_id: 3                    # un proyecto de CLASIFICACIÓN (el proyecto de investigación sale de él)
    timezone: Europe/Madrid          # debe ser la de las locations de los deployments
    timezone_ignore_dst: false       # y esto también
    managers:                        # opcional
      - username: ana
    deployments:
      - deployment_id: don01-2024a   # un deployment existente del proyecto de investigación del proyecto
        resources:
          - name: don01-2024a_0001
            file: IMG_0001.JPG       # res/don01-2024a/IMG_0001.JPG en el ZIP
            date_recorded: '2024-03-01T10:00:00+01:00'
            mime_type: image/jpeg    # opcional, como file_width, file_height, file_size, file_fps, file_duration
```

y el ZIP tiene `res/don01-2024a/IMG_0001.JPG`, es decir `<resources_dir>/<deployment_id>/<file>`.

Lo que necesita (comprobado en Trapper v1 y v2, salvo lo que dice *en el código de Trapper*):

- El **proyecto de clasificación** y los **deployments** deben existir y la cuenta debe poder subir al proyecto. El SDK
  crea deployments por [importación](deployments.md#importar-despliegues-acceso-de-escritura), y proyectos de
  clasificación solo en v1 (`client.classification_projects.create()`).
- La `timezone` y `timezone_ignore_dst` del YAML deben coincidir con las de las locations de los deployments, o
  Trapper lo rechaza.
- La cuenta necesita **acceso al uploader** (en v2 una *cuenta de uploader HTTP*, véase [versiones](versions.md)), y en
  **v1 el uploader lo sirve el nginx de Trapper**: un servidor de desarrollo en su propio puerto contesta `404` al login.
- *En el código de Trapper:* un fichero idéntico (mismo contenido) a otro que ya está en el deployment, o con una
  extensión que Trapper no acepta, se **omite** y queda en un fichero `.log` junto al ZIP, sin que falle el resto.
- En **v2 los ficheros subidos pueden tardar un momento en estar en su sitio**: si `trigger_collection()` contesta
  `NotFoundError` («not found in your upload directory») justo después de la subida, espera un par de segundos y
  vuelve a llamarla.
- `trigger_ai_pipeline` es `True` por defecto y lanza la detección de IA sobre los resources nuevos; pasa `False` para
  evitarlo.
- *En el código de Trapper:* las miniaturas y las vistas previas se generan después de crear los resources, así que
  `resources.download(pk, ..., kind="thumbnail")` puede dar `NotFoundError` durante un momento. Una vez generadas se
  descargan (comprobado en v1).

## Lanzar el procesado de una colección subida por FTP

`trigger_collection()` inicia el procesado de un paquete de datos (una definición YAML y un ZIP) que **ya está en la
carpeta propia de la cuenta en el servidor**: no sube nada (para eso está el uploader).

```python
response = client.collections.trigger_collection(
    payload={
        "yaml_file": "package_123.yaml",
        "zip_file": "package_123.zip",
        "remove_zip": False,
    },
)
print(response.json()["data"]["task_id"])
```

`yaml_file` y `zip_file` son obligatorios; `remove_zip` (por defecto `False`), `extract_metadata` (por defecto `False`)
y `trigger_ai_pipeline` (por defecto `True`) son opcionales. Trapper comprueba la definición YAML y lanza una tarea en
segundo plano (se ejecuta en la propia petición solo si el servidor tiene Celery desactivado), así que un `200`
significa que **se inició**, no que la colección exista. La respuesta es
`{"data": {"message": ..., "errors": ..., "task_id": ...}}`. Un nombre que falta o un YAML inválido es un
`BadRequestError` (los problemas están en `data.errors`), y un fichero que no está en la carpeta de la cuenta es un
`NotFoundError`; con `raise_on_error=False` se devuelve la respuesta cruda.
