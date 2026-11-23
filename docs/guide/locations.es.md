# Localizaciones

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — `import_locations()` funciona en ambas pero se comporta de forma distinta (ver más abajo). Consulta [Versiones de Trapper](versions.md).

`client.locations` — acceso de lectura y escritura a las localizaciones de fototrampeo.

**Endpoint:** `GET /geomap/api/locations` (listado + detalle), `GET /geomap/api/locations/export/` (exportación CSV).

Por lo demás, la API REST es de solo lectura para este recurso; consulta [Importar localizaciones](#importar-localizaciones-acceso-de-escritura)
más abajo para la única operación de escritura que admite este componente.

## Filtros

| Parámetro | Tipo | Descripción |
|---|---|---|
| `name` | cadena | Coincidencia parcial, sin distinguir mayúsculas, en el nombre de la localización |
| `description` | cadena | Coincidencia parcial, sin distinguir mayúsculas, en la descripción |
| `owner` | booleano | `true` = solo las localizaciones del usuario actual |
| `owners` | lista de PK | Filtra por las PK de uno o más propietarios |
| `research_project` | lista de PK | Filtra por uno o más proyectos de investigación |
| `locations_map` | lista de PK | Filtra por localizaciones asociadas a un mapa |
| `deployments` | lista de PK | Filtra las localizaciones que tienen esos despliegues |
| `search` | cadena | Búsqueda de texto global en `location_id`, `name`, `description`, `county`, `city` y el nombre de usuario del propietario |

## Los seis patrones de acceso

```python
# Una página
page = client.locations.get(page=1, page_size=25)

# Todas las páginas unidas
result = client.locations.get_all(page_size=100)

# Iteración perezosa (all() es lo mismo; usa el que se lea mejor)
for loc in client.locations.where(research_project=1):
    print(loc)
for loc in client.locations.all():
    print(loc)

# Por propietario y texto libre
for loc in client.locations.where(owner=True, search="camera"):
    print(loc)

# Un solo elemento
loc = client.locations.find(42)

# Exportación a CSV (también admite filtros)
client.locations.export(file="locations.csv")
client.locations.export(query={"research_project": 5}, file="project5_locations.csv")
```

Consulta [Uso](../usage.md) si algo de esto te resulta desconocido: es la misma interfaz en todos los componentes.

## Coordenadas

Trapper devuelve las coordenadas de una location como una sola cadena, con la **longitud primero**
(`"-6.44, 37.05"`), en v1 y en v2. `Location.coordinates` la conserva tal como llega, y `longitude` y
`latitude` la dan como números:

```python
loc = client.locations.find(16)
loc.coordinates         # "-6.44, 37.05"
loc.longitude           # -6.44
loc.latitude            # 37.05
```

Valen `None` cuando las coordenadas faltan, no se pueden leer o están fuera de rango (longitud más allá de
±180, latitud más allá de ±90): una location rara no rompe un listado. Se leen de `coordinates` cada vez y
no son campos del modelo, así que `model_dump()` no cambia. Las filas de `export(file=None)` ya llevan
`longitude` y `latitude`.

## Campos: la lista y la exportación

Trapper da una location en dos formas, y **ninguna tiene todos los campos**. `where()`, `get()` y `find()`
devuelven una `Location`, construida con el JSON de Trapper; `export(file=None)` devuelve un
`LocationExport` por cada fila de su CSV. Comprobado en Trapper v1 y v2:

| Campo | `Location` (`find()`, `get()`, `where()`) | `LocationExport` (`export(file=None)`) |
|---|---|---|
| `pk`, `location_id`, `description`, `timezone` | sí | sí |
| `name`, `owner`, `owner_profile`, `is_public`, `date_created` | **sí** | no |
| `city`, `county`, `state` | **sí** (no en v2) | no |
| `country` | sí (no en v2) | **sí** |
| Coordenadas | `coordinates`, una cadena, y `longitude` y `latitude` leídas de ella | `longitude` y `latitude` |
| Research project | `research_project`, su **acrónimo** | `research_project_id`, su **clave primaria** |
| `ignore_dst` | no | **sí** |
| `habitat` | no | **sí** |
| `coordinate_uncertainty`, `managers` | no | no |

Así que para leer el `ignore_dst` de una location, o la clave primaria de su research project, usa la
exportación; para leer su nombre o su propietario, usa la lista. `coordinate_uncertainty` y `managers`
existen en Trapper pero no están en ninguna de las dos, y no se pueden leer. Cuando necesites las dos
cosas, únelas por `pk`; dale a la exportación los mismos filtros que a la lista para que devuelvan las
mismas locations:

```python
filters = {"research_project": 3}
by_pk = {row.pk: row for row in client.locations.export(query=filters, file=None)}

for loc in client.locations.where(**filters):
    row = by_pk.get(loc.pk)
    print(loc.name, loc.longitude, row.ignore_dst, row.research_project_id)
```

Trapper construye cada forma con su propio serializador y su propia lista de campos, y por eso difieren
(entrada 23 de `TRAPPER_API_IMPROVEMENTS.md`).

## Importar localizaciones (acceso de escritura)

`/geomap/api/locations` es de solo lectura, así que `import_locations()` lo resuelve simulando el
formulario `geomap/location/import/` de la interfaz web clásica, con autenticación por cookie/sesión en
lugar del token de la API (consulta [`APIClientBase.session_login`](../api/api_client_base.md)).

En **Trapper v2**, el mismo método envía la petición a la acción de importación del admin de Django
(`admin/geomap/location/import-locations/`). La cuenta debe ser un usuario staff con permiso de
creación, y el servidor importa de forma asíncrona: `True` significa que la tabla superó la validación
y quedó en cola. Las tablas rechazadas lanzan `APIError` con el mensaje del servidor y los errores por
fila.

!!! warning "No es un contrato estable de la API"
    Esto depende de un formulario HTML sin versionar, no de un endpoint documentado: un cambio de
    Trapper en esa página puede romperlo sin avisar. Requiere `user_name`/`user_password` (la
    dirección de *correo* de la cuenta en servidores con `ACCOUNT_LOGIN_METHODS = {"email"}`); un
    token por sí solo no puede autenticarlo. Consulta la advertencia completa en el docstring del
    método antes de depender de ello.

```python
client.locations.import_locations(
    file="locations.csv",
    research_project=7,       # obligatorio: ver la nota más abajo
    timezone="Europe/Madrid", # obligatorio: ver la nota más abajo
)
```

!!! note "`research_project` y `timezone` son obligatorios, aunque los campos del servidor digan lo contrario"
    El `LocationImportForm` del servidor declara ambos campos con `required=False`, pero:

    - `clean_research_project()` rechaza un valor ausente con *"You have to select a research
      project."*: una respuesta `200` (formulario vuelto a mostrar) fácil de confundir con un éxito si
      solo compruebas el código de estado.
    - `timezone` es peor: nada rechaza un valor vacío durante la importación. El servidor guarda las
      localizaciones con `Location.objects.bulk_create()`, que **se salta la validación normal del
      modelo**, de modo que una zona horaria vacía u omitida crea en silencio localizaciones con un
      valor de `timezone` corrupto. No falla nada hasta *más tarde*, cuando algo lista o filtra esas
      localizaciones (esta API, o el propio listado de la interfaz web clásica) y el serializador
      tropieza con el valor erróneo, normalmente con un `500` en una petición aparentemente sin
      relación, mucho después de que la importación informara de éxito. Este método exige `timezone`
      de antemano precisamente para evitar crear ese tipo de corrupción latente y difícil de
      diagnosticar.

### Esperar a que la importación termine

En Trapper v2 la importación se ejecuta en segundo plano: que `import_locations()` devuelva `True`
significa que la tabla se validó y se puso en cola, no que las filas ya existan. Ninguna de las dos
versiones expone la tarea de importación a través de la API, así que `wait_for_import()` comprueba el
resultado: consulta periódicamente hasta que todos los `locationID` aparecen en el listado:

```python
client.locations.import_locations(file="locations.csv", research_project=1, timezone="Europe/Madrid")
client.locations.wait_for_import(["don-01", "don-02"], timeout=60)   # lanza TimeoutError si faltan
```

Pasa `raise_on_timeout=False` para recibir `False` en su lugar. Funciona igual en v1.

También hay un script listo para ejecutar: [`examples/import_locations.py`](https://github.com/wildintelproject/wildintelproject-trapper-sdk/blob/refactor/examples/import_locations.py).

### Qué obtienes en la excepción cuando se rechaza el CSV

Si el CSV falla la validación de tabla del servidor (columnas incorrectas o ausentes, un `locationID`
que ya existe en este proyecto de investigación, ...), el `err.APIError` lanzado incluye los mensajes
reales por fila, no solo el aviso genérico. Por ejemplo:

```
Location import failed (status 200): locationID 'dona-001' already exists; longitude must be a number
```

El servidor presenta esos detalles como un bloque JSON para un widget JS, no como texto HTML plano;
consulta [`APIClientBase._extract_html_error_text`](../api/api_client_base.md) para ver cómo se extraen.

### Subir un CSV muy grande: `split`

Este endpoint no tiene protocolo de subida por fragmentos o reanudable: a diferencia del componente
`HTTPUploader` (un cargador por fragmentos de verdad, para otro endpoint), es un simple POST de
formulario en una sola petición. Si un CSV grande se rechaza o agota el tiempo, pasa `split=True` para
dividirlo en varios CSV más pequeños y autocontenidos (cada uno repite la fila de cabecera) e importarlos
de uno en uno:

```python
client.locations.import_locations(
    file="huge_locations.csv",
    research_project=7,
    timezone="Europe/Madrid",
    split=True,
    delay=2,        # segundos entre fragmentos; por defecto 1
    chunk_size=512 * 1024,  # bytes por fragmento; también es el valor por defecto
)
```

`split` no es compatible con `gpx_file` (lanza `ValueError`): dividir solo tiene sentido para la ruta
del CSV, y el servidor rechaza de todos modos una petición con ambos tipos de fichero. Con
`raise_on_error=True` (el valor por defecto), toda la llamada lanza una excepción en cuanto falla un
fragmento, sin subir el resto; con `raise_on_error=False` sube todos los fragmentos de todos modos y
devuelve `False` si alguno falló.

### Reintentar un fragmento que agota el tiempo: `retry_attempts`

Si un fragmento sigue siendo demasiado grande o lento para el servidor, la petición puede fallar con un
tiempo de espera a nivel de red (en lugar de una respuesta de error normal) antes de que el servidor
llegue a responder. Eso se reintenta automáticamente, con [tenacity](https://github.com/jd/tenacity) y
espera exponencial, hasta `retry_attempts` veces:

```python
client.locations.import_locations(
    file="huge_locations.csv",
    research_project=7,
    timezone="Europe/Madrid",
    split=True,
    chunk_size=128 * 1024,  # prueba fragmentos más pequeños si el servidor sigue agotando el tiempo
    retry_attempts=5,       # por defecto 3
    retry_min_wait=2,       # segundos, por defecto 1
    retry_max_wait=30,      # segundos, por defecto 10
)
```

Solo se reintentan los fallos a nivel de red (tiempos de espera, conexiones reiniciadas, ...), nunca una
respuesta de error HTTP (un 4xx/5xx del servidor es un fallo de validación, no algo que arregle un
reintento). Usa `retry_attempts=1` para desactivar los reintentos.

## Relacionado: localizaciones como GeoJSON

Para dibujar mapas, usa [`client.locations_geojson`](locations_geojson.md): es otro endpoint que
devuelve un único `FeatureCollection` GeoJSON, con su propio conjunto de filtros (caja delimitadora,
radio, ...). Solo está disponible en Trapper v1.
