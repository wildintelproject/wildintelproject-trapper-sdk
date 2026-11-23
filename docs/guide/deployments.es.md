# Despliegues

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — `import_deployments()` funciona en ambas pero se comporta de forma distinta (ver más abajo), y `geojson()` es **solo v2**. Consulta [Versiones de Trapper](versions.md).

`client.deployments` — despliegues de cámaras en una localización, durante un intervalo de tiempo.

**Endpoints:** `GET /geomap/api/deployments` (listado + detalle), `GET /geomap/api/deployments/export/` (exportación CSV).

Por lo demás, la API REST es de solo lectura para este recurso; consulta [Importar despliegues](#importar-despliegues-acceso-de-escritura)
más abajo para la única operación de escritura que admite este componente.

## Filtros

| Parámetro | Tipo | Descripción |
|---|---|---|
| `location` | int o lista | Filtra por ID(s) de localización |
| `research_project` | int o lista | Filtra por ID(s) de proyecto de investigación |
| `tags` | int o lista | Filtra por ID(s) de etiqueta |
| `owner` | bool | Filtra por propiedad del usuario actual |
| `sdate_from`, `sdate_to` | fecha (ISO) | Filtra por rango de fecha de inicio |
| `edate_from`, `edate_to` | fecha (ISO) | Filtra por rango de fecha de fin |
| `classification_project` | int | Filtra por ID de proyecto de clasificación |
| `correct_setup` | bool | Filtra por corrección de la configuración |
| `correct_tstamp` | bool | Filtra por corrección de las marcas de tiempo |
| `search` | str | Busca en `deployment_id` o en el nombre de usuario del propietario |

!!! warning "Trapper ignora un filtro que no conoce"
    Un parámetro que no es un filtro de Trapper (una errata, `colls`, `ordering`, `radius`...) se **ignora sin
    error** y la lista vuelve sin filtrar. El SDK conoce los filtros de cada versión de Trapper y, si pasas otro,
    emite un `UnknownFilterWarning` que lo nombra (la petición se envía igualmente). Además de los de la tabla, la
    lista aplica `pk`, `deployment_code`, `deployment_id`, `setup_by`, `camera_*`, `detection_distance`, `bait_type`,
    `feature_type`, `habitat`, `session`, `array`, `comments`, `date_created`, `managers`, `start_date`, `end_date`,
    `is_incomplete`, `view_quality`, `capture_method` y `status`, y v2 aplica también `in_bbox`. Para silenciarlo:
    `warnings.simplefilter("ignore", err.UnknownFilterWarning)`.

## Los seis patrones de acceso

```python
# Una página
page = client.deployments.get(page=1, page_size=25, research_project=3)

# Todas las páginas unidas
result = client.deployments.get_all(page_size=100)

# Iteración perezosa (all() es lo mismo)
for dep in client.deployments.where(location=42, sdate_from="2024-01-01"):
    print(dep)
for dep in client.deployments.all():
    print(dep)

# Un solo elemento
dep = client.deployments.find(99)

# Exportación a CSV
client.deployments.export(file="deployments.csv")
```

Consulta [Uso](../usage.md) si algo de esto te resulta desconocido: es la misma interfaz en todos los componentes.

No hay filtro por colección: la API de despliegues de Trapper no lo tiene, e ignora en silencio
cualquier parámetro que no conoce (como `colls`), devolviendo todos los despliegues. Usa el atajo de
más abajo.

## Atajo: por colección

`by_collection()` devuelve los despliegues con al menos un recurso en una colección. La API de
despliegues no puede filtrar por colección, pero la de recursos sí puede filtrar por colección **y**
despliegue a la vez: cada despliegue candidato (lo que devuelva `where()` para los filtros que pases) se
comprueba con una única petición de recursos, con `max_workers` (8 por defecto) en paralelo. Acota los
candidatos, normalmente con `research_project`: sin ningún filtro se comprueban todos los despliegues
del servidor.

```python
# Despliegues del proyecto de investigación 3 con imágenes en la colección 5
for dep in client.deployments.by_collection(5, research_project=3):
    print(dep)

# ...con cuántas imágenes tiene cada uno allí
for dep, count in client.deployments.by_collection_with_counts(5, research_project=3):
    print(dep.deployment_id, count)

# Exportarlos a CSV
client.deployments.export_by_collection(5, research_project=3, file="deps.csv")
```

`collection_id` es la pk propia de la colección de almacenamiento: `collection_pk` en la lista de
colecciones de un proyecto de clasificación (`classification_projects.get_all_project_collections()`).

## GeoJSON (solo Trapper v2)

`geojson()` devuelve los despliegues como un `FeatureCollection` GeoJSON. Sustituye a
[`client.maps`](maps.md) y [`client.locations_geojson`](locations_geojson.md), que Trapper v2 eliminó;
en un servidor v1 lanza `UnsupportedVersionError`.

```python
fc = client.deployments.geojson(classification_project=2, species=[3, 7])
for feature in fc["features"]:
    lon, lat = feature["geometry"]["coordinates"]
    print(feature["properties"]["deploymentID"], lon, lat)
```

| Parámetro | Descripción |
|---|---|
| `classification_project` | Conserva los despliegues vinculados a este proyecto de clasificación; limita `observation_type` y `species` a sus clasificaciones |
| `observation_type` | Un valor o una lista (`"animal"`, `["animal", "human"]`) |
| `species` | Una pk de especie o una lista |
| `start_date_gte`, `end_date_lte` | Despliegues que empiezan desde, o acaban hasta, una fecha (`YYYY-MM-DD`) |
| `refresh` | Omite la caché de una hora del servidor para esta consulta |

Solo se devuelven los despliegues a los que puede acceder el usuario actual.

## Campos: la lista y la exportación

Igual que las locations, un despliegue viene en dos formas y ninguna tiene todos los campos. `where()`,
`get()` y `find()` devuelven un `Deployment` (el JSON de Trapper): `pk`, `deployment_code`, `deployment_id`,
`location` (el **pk** de la location), `location_id`, `start_date`, `end_date`, `owner`, `research_project`
(su **acrónimo**), `tags`, `correct_setup` y `correct_tstamp`. `export(file=None)` devuelve un
`DeploymentExport` por cada fila del CSV, que tiene en cambio los campos de la cámara y la instalación
(`setup_by`, `camera_*`, `detection_distance`, `bait_use`, `feature_type`, `habitat`, `session`, `array`,
`comments`, `longitude`, `latitude`, `location_name`) pero **no** el propietario, el proyecto de investigación
ni `correct_setup` y `correct_tstamp`. Las dos tienen `pk`, `deployment_id`, `location_id`, `start_date`,
`end_date` y `tags`. Comprobado en Trapper v1 y v2.

`start_date` y `end_date` son objetos `datetime` con zona horaria en las dos formas, aunque Trapper las escribe
distinto (`2024-01-01T00:00:00+01:00` en el JSON, `2024-01-01T00:00:00+0100` en el CSV), así que se pueden
comparar y ordenar leas la que leas. Una fecha que no se puede leer se conserva como el texto con el que llegó, y
una vacía es `None`. `export(file="x.csv")` las escribe de vuelta como texto ISO con los dos puntos (`+01:00`);
`raw=True` conserva la escritura de Trapper.

El CSV de Trapper no tiene columna para `session`, `array`, `tags` ni `bait_type`: pone las dos primeras en
`deploymentGroups` (`session:S | array:A`) y las etiquetas en `deploymentTags`, con `baitType:<valor>` añadido
cuando el despliegue tiene un tipo de cebo. `DeploymentExport` las lee de ahí, así que `tags` solo tiene las
etiquetas y `bait_type` el cebo. Para obtener el CSV tal como lo envía Trapper, usa
`export(file=..., raw=True)`.

## Importar despliegues (acceso de escritura)

`/geomap/api/deployments` es de solo lectura, así que `import_deployments()` lo resuelve simulando el
formulario `geomap/deployment/import/` de la interfaz web clásica, con autenticación por cookie/sesión
en lugar del token de la API (consulta [`APIClientBase.session_login`](../api/api_client_base.md)).

En **Trapper v2**, el mismo método envía la petición a la acción de importación del admin de Django
(`admin/geomap/deployment/import-deployments/`). La cuenta debe ser un usuario staff con permiso de
creación, y el servidor importa de forma asíncrona: `True` significa que la tabla superó la validación
y quedó en cola, así que consulta `client.deployments` si necesitas que las filas ya estén. Las tablas
rechazadas lanzan `APIError` con el mensaje del servidor y los errores por fila.

!!! warning "No es un contrato estable de la API"
    La misma advertencia que en la [importación de localizaciones](locations.md#importar-localizaciones-acceso-de-escritura):
    depende de un formulario HTML sin versionar y requiere `user_name`/`user_password` (el *correo* de
    la cuenta). Consulta el docstring del método para la advertencia completa.

A diferencia de las localizaciones, aquí `timezone` es **obligatorio**: el formulario del servidor no
tiene valor por defecto. `research_project` también es obligatorio (por la misma razón que en las
[localizaciones](locations.md#importar-localizaciones-acceso-de-escritura): el campo se declara
`required=False`, pero su `clean_research_project()` rechaza un valor ausente):

```python
client.deployments.import_deployments(
    file="deployments.csv",
    timezone="Europe/Madrid",           # obligatorio
    research_project=7,                 # obligatorio
    classification_project=3,           # opcional, vincula todos los despliegues importados a él
    create_locations=True,              # requiere columnas locationID/longitude/latitude en el CSV
    update=False,                       # True actualiza despliegues existentes (requiere una columna _id)
)
```

También hay un script listo para ejecutar: [`examples/import_deployments.py`](https://github.com/wildintelproject/wildintelproject-trapper-sdk/blob/refactor/examples/import_deployments.py).

### Esperar a que la importación termine

En Trapper v2 la importación se ejecuta en segundo plano: que `import_deployments()` devuelva `True`
significa que la tabla se validó y se puso en cola, no que las filas ya existan. Ninguna de las dos
versiones expone la tarea de importación a través de la API, así que `wait_for_import()` comprueba el
resultado: consulta periódicamente hasta que todos los `deploymentID` aparecen en el listado:

```python
client.deployments.import_deployments(file="deployments.csv", research_project=1, timezone="Europe/Madrid")
client.deployments.wait_for_import(["DON01-2024A", "DON01-2024B"], timeout=60)   # lanza TimeoutError si faltan
```

Pasa `raise_on_timeout=False` para recibir `False` en su lugar. Funciona igual en v1.

### Actualizar despliegues

Trapper no tiene un endpoint para editar un despliegue, pero la importación actualiza los que ya existen cuando
recibe `update=True` y una columna `_id` con sus claves primarias. El CSV que exporta Trapper tiene esa columna,
así que la forma de corregir despliegues es **exportar, editar, importar**:

```python
import csv

# 1. Exporta los despliegues tal como los envía Trapper (raw=True conserva la columna _id y la cabecera)
path = client.deployments.export(file="deployments.csv", raw=True, research_project=7)

# 2. Edita el CSV: cambia las celdas que quieras, conserva la cabecera y el _id
with open(path, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
for row in rows:
    if row["deploymentID"] == "don01-2024a":
        row["cameraHeight"] = "1.25"
        row["habitat"] = "dehesa"
with open("edited.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

# 3. Impórtalo con update=True y espera a que estén los valores nuevos
client.deployments.import_deployments(
    file="edited.csv", research_project=7, timezone="Europe/Madrid", update=True,
)
client.deployments.wait_for_update({"don01-2024a": {"camera_height": 1.25, "habitat": "dehesa"}})
```

`import_deployments()` devuelve `True` cuando la tabla se valida y queda en cola, en v1 y en v2: los cambios se
aplican un momento después. `wait_for_import()` no puede saberlo, porque los IDs ya existen, así que
`wait_for_update()` consulta la exportación hasta que cada despliegue tiene los valores que le das, con los
nombres de campo de `DeploymentExport` (los números se comparan con tolerancia). Lanza `TimeoutError`, o devuelve
`False` con `raise_on_timeout=False`, si no llegan en `timeout` segundos. Dale el ID guardado: Trapper convierte
en *slug* el `deploymentID` de una importación (`"Don 01"` se guarda como `"don-01"`). Comprobado en Trapper v1 y v2. Como en el resto de las importaciones, la cuenta debe ser staff en v2.

### Qué obtienes en la excepción cuando se rechaza el CSV

Igual que en las [localizaciones](locations.md#que-obtienes-en-la-excepcion-cuando-se-rechaza-el-csv):
si el CSV falla la validación de tabla del servidor (columnas incorrectas o ausentes, un
`deploymentID`/`locationID` que ya existe, ...), el `err.APIError` lanzado incluye los mensajes reales
por fila, extraídos del informe de validación incrustado del servidor. Por ejemplo:

```
Deployment import failed (status 200): locationID 'dona-001' already exists
```

### Subir un CSV muy grande: `split`

Mismo mecanismo que en las [localizaciones](locations.md#subir-un-csv-muy-grande-split): este endpoint
no tiene protocolo de subida por fragmentos o reanudable, así que `split=True` divide el CSV en varios
fragmentos más pequeños y autocontenidos (cada uno repite la fila de cabecera) y los importa de uno en
uno, esperando `delay` segundos (por defecto `1`) entre subidas:

```python
client.deployments.import_deployments(
    file="huge_deployments.csv",
    timezone="Europe/Madrid",
    research_project=7,
    split=True,
    delay=2,
    chunk_size=512 * 1024,  # bytes por fragmento; también es el valor por defecto
)
```

!!! warning "`split` + `create_locations=True`"
    Cada fragmento se importa como una petición independiente, así que si el mismo `locationID`
    aparece en más de un fragmento, el servidor intentará crear esa localización de nuevo en cada
    fragmento que la mencione: no recuerda las localizaciones creadas por un fragmento anterior. Combina
    `split` con `create_locations=True` solo si sabes que cada `locationID` cae dentro de un único
    fragmento, o crea las localizaciones por separado e importa con `create_locations=False`.

Con `raise_on_error=True` (el valor por defecto), toda la llamada lanza una excepción en cuanto falla un
fragmento, sin subir el resto; con `raise_on_error=False` sube todos los fragmentos de todos modos y
devuelve `False` si alguno falló.

### Reintentar un fragmento que agota el tiempo: `retry_attempts`

Mismo mecanismo que en las [localizaciones](locations.md#reintentar-un-fragmento-que-agota-el-tiempo-retry_attempts):
un tiempo de espera a nivel de red en un fragmento demasiado grande o lento se reintenta
automáticamente (tenacity, espera exponencial) mediante `retry_attempts`/`retry_min_wait`/`retry_max_wait`;
nunca una respuesta de error HTTP, que es un fallo de validación que un reintento no arregla. Usa
`retry_attempts=1` para desactivar los reintentos.
