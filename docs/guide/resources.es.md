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

## Descargar el fichero

La API REST lista los resources pero no sirve sus ficheros: `url` y `url_original` son rutas de una vista web
clásica (`/storage/resource/media/<pk>/file/`) que **no acepta el token de la API**. Con un token, o sin sesión,
contesta `404`, y lo hace tanto cuando el fichero no existe como cuando la cuenta no puede verlo. `download()`
inicia sesión con `user_name` y `user_password` (el *email* de la cuenta en servidores que entran por email), como
hacen las importaciones, y guarda el fichero:

```python
client = TrapperClient(base_url=..., access_token=..., user_name="yo@example.org", user_password="...")

path = client.resources.download(29, "images/")                          # un directorio: se guarda como 29-original.jpg
path = client.resources.download(29, "photo.jpg")                        # o un nombre de fichero
thumb = client.resources.download(29, "thumb.jpg", kind="thumbnail")     # "original", "preview" o "thumbnail"

for res in client.resources.where_by_collection(5):
    client.resources.download(res.pk, "collection-5/")
```

- El fichero se escribe a disco por partes, en un `.part` temporal que se mueve a su sitio cuando está completo, así
  que un fallo nunca deja un fichero a medias.
- Los fallos de red y las respuestas `502`/`503`/`504` se reintentan con espera exponencial (tenacity):
  `retry_attempts` (3, contando el primer intento; `1` lo desactiva), `retry_min_wait` y `retry_max_wait`. Una
  descarga cortada empieza otra vez desde el principio. Un `404` y cualquier otra respuesta no se reintentan.
- Un `404` lanza `NotFoundError` diciendo que puede ser el fichero o el permiso. La vista previa y la miniatura
  pueden no existir si Trapper no las generó.
- `download()` lanza `ValueError` si el cliente no tiene `user_name`/`user_password`.
- Un Trapper que no está detrás del proxy que sirve sus ficheros (un servidor de desarrollo en su propio puerto)
  contesta `200` con el cuerpo vacío y una cabecera `X-Accel-Redirect`; `download()` lanza `APIError` diciéndolo
  en vez de guardar un fichero vacío. Comprobado en Trapper v2 (el JPEG original); en v1, solo contra uno así.

!!! warning "No es un contrato estable de la API"
    Depende de una vista web sin versionar, como las importaciones.

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
