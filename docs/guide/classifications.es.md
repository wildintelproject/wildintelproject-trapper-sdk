# Clasificaciones

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — salvo `import_classifications(overwrite_attrs=True)`, que es **solo v1**. Consulta [Versiones de Trapper](versions.md).

`client.classification_results` — observaciones de clasificación finales (aprobadas).

**Endpoints:**

- `GET /media_classification/api/classifications` (listado + detalle)
- `GET /media_classification/api/classifications/results/{project_pk}/` — exportación CSV/modelos de las observaciones de un proyecto
- `POST /media_classification/api/classifications/import/` — importa observaciones desde un CSV

## Filtros

| Parámetro | Tipo | Descripción |
|---|---|---|
| `project` | PK | Se filtra automáticamente por la URL con los métodos de exportación por proyecto de más abajo; no hace falta allí |
| `owner` | booleano | `true` = recursos donde el usuario es propietario/gestor |
| `deployment` | lista de PK | Filtra por PK de despliegue |
| `collection` | lista de PK | Filtra por PK de colección |
| `locations_map` | PK separadas por comas | Filtra por PK de localización |
| `rdate_from` / `rdate_to` | fecha | Rango de `date_recorded` |
| `rtime_from` / `rtime_to` | HH:MM | Rango de hora del día |
| `ftype` | opción | Tipo de recurso (IMAGE, VIDEO, ...) |
| `bboxes` | booleano | Tiene cajas delimitadoras |
| `user` | lista de PK | Filtra por PK de usuario propietario |
| `approved` | booleano | Tiene una clasificación FINAL aprobada |
| `feedback` | booleano | Es una clasificación de retroalimentación |
| `species` | lista de PK | Filtra por PK de especie |
| `observation_type` | opción | Filtra por tipo de observación |
| `sex` | opción | Filtra por sexo |
| `age` | opción | Filtra por edad |
| `confidence` | número | `dynamic_attrs.classification_confidence >= valor` |
| `ai_provider` | lista de PK | Filtra por PK de proveedor de IA |

## Los seis patrones de acceso

```python
page = client.classification_results.get(page=1, page_size=50, approved=True)
for row in client.classification_results.where(species=42):
    print(row)
result = client.classification_results.get_all(page_size=100)
row = client.classification_results.find(1)
```

Consulta [Uso](../usage.md) si algo de esto te resulta desconocido: es la misma interfaz en todos los componentes.

## Exportación de observaciones, limitada a un proyecto

El endpoint de exportación devuelve un esquema *distinto* al anterior: filas de observación con formato
CamtrapDP o de Trapper (`ClassificationRecordExport`), según lo que devuelva el servidor:

```python
# Una página
page = client.classification_results.get_project_results(
    project_pk=7, page=1, page_size=50, approved=True,
)
for row in page.results:
    print(row.observationID, row.scientificName)

# Iteración perezosa
for row in client.classification_results.where_project_results(project_pk=7):
    print(row)

# Directamente a CSV
client.classification_results.export_project_results(project_pk=7, file="observations.csv")

# O recibir instancias de modelo en lugar de un fichero
records = client.classification_results.export_project_results(project_pk=7, file=None)
```

Campo adicional en los endpoints de exportación:

| Parámetro | Tipo | Por defecto | Descripción |
|---|---|---|---|
| `camtrapdp` | booleano | `True` | `True` = filas en el estándar CamtrapDP, `False` = formato interno de Trapper |

## Importar observaciones desde un CSV

A diferencia de la importación de localizaciones y despliegues (que simula un formulario HTML), este es un
**endpoint REST real, autenticado con token**: la forma correcta de hacer una importación, y el modelo
al que las soluciones de localizaciones y despliegues explícitamente no llegan.

```python
result = client.classification_results.import_classifications(
    project_id=7,
    file="observations.csv",
    approve=True,
    import_bboxes=True,
    import_expert_classifications=True,
    import_ai_classifications=False,   # pon True + ai_provider_id para importar también filas de IA
    overwrite_attrs=False,             # True solo funciona en Trapper v1
)
print(result.data.message, result.data.task_id)
```

Si el servidor ejecuta la importación como una tarea de Celery, `result.data.task_id` tiene valor y el
mensaje indica que se está ejecutando de forma asíncrona; si no, el mensaje refleja el resultado
síncrono.

Por defecto, `check_table=True` comprueba la tabla en local antes de enviarla (columnas `_id` y
`classificationMethod` presentes, `sex` solo `female`/`male`) y lanza un `ValueError` que nombra el
problema, en lugar de dejar que Trapper responda con un HTTP 500 sin explicación. Usa
`check_table=False` para omitir la comprobación.

### Dividir CSV grandes

Igual que `import_locations`/`import_deployments`, acepta `split`/`delay`/`chunk_size` para dividir un
CSV grande en varios fragmentos más pequeños y autocontenidos (cada uno repite la fila de cabecera),
subidos de uno en uno con una pausa entre ellos:

```python
results = client.classification_results.import_classifications(
    project_id=7, file="huge_observations.csv",
    split=True, delay=2,  # fragmentos de <=512 KiB, separados 2 s
)
for r in results:
    print(r.data.message, r.data.task_id)
```

Con `split=True` el valor devuelto es una **lista** de resultados (uno por fragmento), en lugar de uno solo.

### Reintentar subidas que agotan el tiempo

Si un fragmento sigue siendo demasiado grande o lento para el servidor, la subida puede fallar con un
tiempo de espera a nivel de red en lugar de una respuesta de error normal.
`retry_attempts`/`retry_min_wait`/`retry_max_wait` reintentan ese modo de fallo concreto (con
[tenacity](https://github.com/jd/tenacity) y espera exponencial), nunca una respuesta 4xx/5xx, porque
es un fallo de validación que un reintento no arregla:

```python
client.classification_results.import_classifications(
    project_id=7, file="observations.csv",
    split=True, chunk_size=128 * 1024,  # fragmentos más pequeños si el servidor sigue agotando el tiempo
    retry_attempts=5, retry_min_wait=2, retry_max_wait=30,
)
```

Usa `retry_attempts=1` para desactivar los reintentos.

!!! note "Este endpoint no lo necesita como las localizaciones y los despliegues"
    A diferencia de las localizaciones y los despliegues, este es un endpoint REST real pensado para
    recibir un fichero completo en una sola petición: recurre a `split` solo si un CSV grande choca
    con un límite de tamaño de petición o agota el tiempo.

!!! note "Esto actualiza clasificaciones existentes: no crea observaciones nuevas"
    La columna `_id` del CSV debe referirse a clasificaciones que **ya existen** en el proyecto de
    destino (el servidor la comprueba contra una lista blanca de PK de clasificación de ese proyecto y
    rechaza cualquier otra). Esta importación vuelve a aplicar datos de clasificación de expertos o de IA
    (especie, recuento, aprobación, ...) a esas filas existentes; no sirve para añadir observaciones
    totalmente nuevas.

!!! warning "Una tabla inválida da un HTTP 500"
    Cuando la tabla no supera la validación, Trapper (v1 y v2) responde con un HTTP 500 sin detalle,
    porque no puede serializar su informe de validación. El `APIError` lo indica y enumera qué revisar.

También hay un script listo para ejecutar: [`examples/import_classifications.py`](https://github.com/wildintelproject/wildintelproject-trapper-sdk/blob/refactor/examples/import_classifications.py).
Tiene un modo `--fetch N` que escribe en un CSV N filas de observaciones *reales* ya existentes en tu
propio proyecto (solo lectura, seguro): como un CSV con valores `_id` inventados siempre será
rechazado, es la forma práctica de obtener algo con lo que probar de verdad.
