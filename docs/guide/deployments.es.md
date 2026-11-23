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
