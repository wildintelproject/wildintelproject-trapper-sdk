# Medios de clasificación

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — el mismo código en ambas. Consulta [Versiones de Trapper](versions.md).

`client.classification_media` — filas de medios (con URL de descarga) de un proyecto de clasificación.

**Endpoint:** `GET /media_classification/api/media/{project_pk}/`.

!!! note "No se puede usar directamente con `get()`/`where()`"
    El endpoint necesita un `project_pk` en su URL, así que llamar a `get()`/`get_all()`/`where()`/
    `all()`/`find()` genéricos, heredados de todos los componentes, no funcionaría aquí: usa los métodos
    `_project_media`/`_collection_media` de más abajo, que resuelven la URL por ti.

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
| `trapper_url` | bool | `True` | Incluye URL absolutas de Trapper para cada medio |
| `trapper_url_token` | bool | `True` | Incluye tokens de acceso en las URL |
| `private_human` | bool | `True` | Incluye la URL de vista previa de humanos |
| `private_vehicle` | bool | `True` | Incluye la URL de vista previa de vehículos |
| `private_species` | list | `[]` | Lista de especies que se ocultan |

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
