# Medios de clasificación

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — el mismo código en ambas. Consulta [Versiones de Trapper](versions.md).

`client.classification_media` — filas de medios (con URL de descarga) de un proyecto de clasificación.

**Endpoint:** `GET /media_classification/api/media/{project_pk}/`.

!!! note "No se puede usar directamente con `get()`/`where()`"
    El endpoint necesita un `project_pk` en su URL, así que llamar a `get()`/`get_all()`/`where()`/
    `all()`/`find()` genéricos, heredados de todos los componentes, no funcionaría aquí: usa los métodos
    `_project_media`/`_collection_media` de más abajo, que resuelven la URL por ti.

## Qué representa

Un **proyecto de clasificación** toma colecciones de resources y registra qué hay en cada uno (su
*clasificación*). `client.classification_media` es la **tabla de media de ese proyecto**: una fila por resource del
proyecto, con la forma del fichero *media* de Camtrap DP (Trapper la construye a partir de la clasificación final
de cada resource, según su código). **No** es una lista de todos los resources de Trapper: un resource que no está
en ningún proyecto de clasificación no tiene fila aquí, y por tanto tampoco URL de descarga con token. Para esos,
véase [Descargar el fichero](resources.md#descargar-el-fichero) en la guía de resources.

Cada fila es un [`Media`](../api/schemas/classifications.md), con las mismas once columnas en Trapper v1 y v2:

| Columna | Qué es |
|---|---|
| `mediaID` | La **clave primaria del resource** (`Resource.pk`) |
| `deploymentID` | El texto `deployment_id` del deployment (`don01-2024a`), no su clave primaria |
| `captureMethod` | Cómo captura el deployment (`activityDetection` en los datos de Trapper) |
| `timestamp` | `date_recorded`, con su desfase UTC (`2024-03-19T13:30:31+0100`) |
| `filePath` | La URL para descargar el fichero, con el token del resource si el fichero es público (véase abajo) |
| `filePublic` | `True` si `filePath` lleva el token, `False` si no |
| `fileName` | El nombre del resource, **sin extensión** (`don01-2024a_0004`) |
| `fileMediatype` | Su tipo MIME (`image/jpeg`) |
| `exifData` | Siempre vacío: Trapper no lo rellena (según su código) |
| `favorite`, `mediaComments` | Marca y comentarios; vacíos en los datos comprobados |

Cómo llega: el servidor manda la tabla entera en un único CSV gzip e **ignora la paginación**. `page_size` no
tiene efecto, y `page=2` devuelve las mismas filas que `page=1`, con `pages=1`. `where_project_media()` y
`get_all` lo manejan bien; no te apoyes en `page` para recorrerla.

!!! note "Lo que hay en cada imagen no está aquí"
    La tabla describe los **resources del proyecto de clasificación** y sus ficheros, no lo que muestran. En una fila
    no hay animal, vehículo, especie, número, sexo ni caja: eso está en los resultados de clasificación del proyecto
    ([`client.classification_results`](classifications.md)). Un resource que no está en ningún proyecto de
    clasificación tampoco tiene fila aquí. Para tener las dos cosas, únelas por `mediaID`:

    ```python
    vistos = {}
    for obs in client.classification_results.where_project_results(7):
        vistos.setdefault(obs.mediaID, []).append(obs.observationType)

    for row in client.classification_media.where_project_media(7):
        print(row.fileName, vistos.get(row.mediaID))    # don01-2024a_0004 ['animal']
    ```

    Los [filtros](#filtros) sí miran la clasificación (`species`, `observation_type`, ...), así que puedes pedir las
    imágenes con un lince, pero la fila que recibes no dice que es un lince.

### Ficheros públicos y privados

`filePath` siempre está, pero solo un fichero **público** lleva `?rt=<token>`, y solo esa URL se puede descargar
sin sesión. Por defecto Trapper oculta las imágenes de **personas** y de **vehículos**: su fila tiene `filePublic`
a falso y una URL sin token, que contesta `404`. Los parámetros extra lo deciden:

- `private_human` y `private_vehicle` (por defecto **ocultan**): `True` oculta los ficheros cuya observación es una
  persona, o un vehículo; `False` los muestra con su token.
- `private_species`: las especies (claves primarias) que se ocultan.
- `trapper_url_token`: `False` deja el token fuera de todas las URLs, así que todas las filas son privadas.

!!! warning "Trapper solo lee el texto exacto `True`"
    Cualquier otra cosa, `true` incluido, es `False` para el servidor. El SDK envía un `True` de Python como
    `true`, así que `private_human=True` **muestra** a las personas, lo contrario de lo que dice, mientras que el
    valor por defecto las oculta. Pasa el texto: `private_human="True"` o `private_human="False"` (hay un issue
    para arreglarlo).

Una tabla de proyecto sin nada que mostrar (un filtro que no deja filas, o un proyecto que la cuenta no puede ver)
es un `BadRequestError` («Empty queryset or you have no permission...») y no una lista vacía; los dos casos no se
pueden distinguir.

## Filtros

| Parámetro | Tipo | Descripción |
|---|---|---|
| `owner` | booleano | `true` = recursos donde el usuario es propietario o gestor |
| `deployment` | lista de PK | Filtra por PK de despliegue |
| `collection` | lista de PK | Filtra por PK de colección |
| `locations_map` | PK separadas por comas | Filtra por PK de localización |
| `rdate_from` / `rdate_to` | fecha | Rango de `date_recorded` |
| `rtime_from` / `rtime_to` | HH:MM | Rango de hora del día sobre `date_recorded` |
| `ftype` | opción | Filtra por tipo de recurso (IMAGE, VIDEO, ...) |
| `classified` | booleano | Clasificado por un usuario |
| `classified_ai` | booleano | Clasificado por IA |
| `approved` | booleano | Clasificación aprobada |
| `bboxes` | booleano | Tiene cajas delimitadoras |
| `species` | lista de PK | Filtra por PK de especie |
| `observation_type` | opción | Filtra por tipo de observación |
| `sex` | opción | Filtra por sexo |
| `age` | opción | Filtra por edad |

**Parámetros adicionales** (independientes del filtrado):

| Parámetro | Tipo | Por defecto | Descripción |
|---|---|---|---|
| `trapper_url` | bool | `True` | Trapper lo lee pero no lo usa: la URL siempre es absoluta (según su código) |
| `trapper_url_token` | bool | `True` | `False` deja el token fuera de todas las URL (todos los ficheros pasan a ser privados) |
| `private_human` | bool | `True` | `True` oculta los ficheros de personas (véase [Ficheros públicos y privados](#ficheros-publicos-y-privados)) |
| `private_vehicle` | bool | `True` | `True` oculta los ficheros de vehículos |
| `private_species` | lista de PK | `[]` | Especies cuyos ficheros se ocultan |

## Medios de todo un proyecto

```python
# Una página
page = client.classification_media.get_project_media(project_pk=7, page_size=200)

# Iteración perezosa
for row in client.classification_media.where_project_media(project_pk=7, deployment=12):
    print(row)

# Exportación a CSV
client.classification_media.export_project_media(project_pk=7, file="media.csv")

# Encontrar una fila de medios por su ID de medio/recurso
row = client.classification_media.get_project_media_by_id(project_pk=7, media_id=4831)
```

## Medios limitados a una colección dentro del proyecto

```python
page = client.classification_media.get_collection_media(project_pk=7, collection_pk=5)

for row in client.classification_media.where_collection_media(project_pk=7, collection_pk=5):
    print(row)

client.classification_media.export_collection_media(
    project_pk=7, collection_pk=5, file="collection_media.csv",
)
```

## Descargar los ficheros

El `filePath` de cada fila de medios es una URL absoluta lista para descargar (ya lleva el token de
acceso del recurso). Es necesario para los recursos privados, porque la vista que sirve los ficheros no
forma parte de la API DRF y no respeta la cabecera `Authorization`.

```python
# Descargar todos los ficheros multimedia de un proyecto
files = client.classification_media.download_project_media_files(
    project_pk=7, output_dir="media",
)

# Lo mismo, pero limitado a una colección, en paralelo y comprimido en un único ZIP
files = client.classification_media.download_collection_media_files(
    project_pk=7, collection_pk=5, output_dir="collection_media",
    parallel=True, compress=True,
)

# Descargar un fichero directamente si ya tienes su URL
path = client.classification_media.download_media_file(
    file_url=row.filePath, file="media_4831.jpg",
)
```

Solo se envía la URL: ni el token de la API ni sesión, así que funciona con solo el token. El fichero se escribe
por partes en un `.part` temporal que se mueve a su sitio cuando está completo, así que una descarga que falla
nunca deja un fichero a medias. Los fallos de red y las respuestas `502`/`503`/`504` se reintentan con espera
exponencial (`retry_attempts`, `retry_min_wait`, `retry_max_wait`); un `404` (fichero que no existe o token que
ya no vale) es un `NotFoundError` y no se reintenta.
