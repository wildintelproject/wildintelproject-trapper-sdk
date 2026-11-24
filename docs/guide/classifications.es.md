# Clasificaciones

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — salvo `import_classifications(overwrite_attrs=True)`, que es **solo v1**. Consulta [Versiones de Trapper](versions.md).

`client.classification_results` — las **clasificaciones finales** de un proyecto de clasificación.

## Qué representa

En un proyecto de clasificación cada resource tiene una **clasificación final**: el registro que guarda el resultado de
ese resource (qué muestra), tomado de la clasificación que alguien hizo o importó y que después se aprobó (según el
código de Trapper). `approved` dice si eso ha ocurrido; los resources que nadie ha clasificado tienen también una
clasificación final, con el tipo de observación `unclassified`. Este componente lee esos registros de tres formas,
cada una con su propia forma (comprobado en Trapper v1 y v2):

| | Lista (`where()`, `find()`) | Tabla de resultados (`where_project_results()`, `export_project_results()`) | Importación |
|---|---|---|---|
| Una fila por | **resource** | **observación** (un resource con dos especies tiene dos filas) | el `_id` de una clasificación final |
| Especie | texto (`"European Rabbit (Oryctolagus cuniculus)"`), sin pk | `scientificName` | `scientificName` |
| `sex`, `lifeStage`, `behavior`, `bboxes` | **no están** | sí | sí |
| Identificador | `pk`, la clave primaria de la clasificación | `_id` (solo con `camtrapdp=False`); `observationID` es solo el **número de fila** de la tabla que pediste (cambia con los filtros) y no está en la lista | `_id` |
| Necesita proyecto | para `deployment` y `collection` | sí, en la URL | sí |

Así que **para saber qué muestra cada imagen, usa la tabla de resultados**; la lista dice qué resources están
clasificados y aprobados, y nada más. Sus `dynamic_attrs` solo llevan `observation_type`, `species` y `count`.

### Qué es cada cosa

- **Clasificación:** lo que una persona (o la IA) decidió sobre un resource. La clasificación de cada usuario sobre un
  resource es un registro propio (`user_classifications`, véase [Clasificaciones de usuario](user_classifications.md));
  la clasificación **final** es el único registro por resource que lee este componente. Cuando se aprueba la
  clasificación de alguien, la final apunta a ella y toma sus valores (según el código de Trapper): es **una**
  clasificación elegida, no una mezcla de varias.
- **Observación:** una cosa vista en el resource, con su tipo (`animal`, `human`, `blank`, ...), especie, `count`,
  `sex`, `lifeStage` y `behavior`. Es una fila de la tabla de resultados. Dos especies en una imagen son dos
  observaciones; una imagen sin nada es una (`blank` o `unclassified`).
- **Caja (bounding box):** una posición opcional de la observación en la imagen (`bboxX`, `bboxY`, `bboxWidth`,
  `bboxHeight`, y la lista `bboxes` con `camtrapdp=False`). Dice *dónde*, no *qué*: lo que hay lo dice la observación,
  y quién lo dijo, `classificationMethod` (`human` o `machine`) y `classifiedBy`. Una observación puede tener varias
  cajas (un conteo de tres) o ninguna.
- **`_id`:** la clave primaria de la clasificación final del resource, igual que el `pk` de la lista. Es el
  identificador estable, y el que necesita la importación.
- **`observationID`:** solo el **número de fila** de la tabla que pediste. Cambia con los filtros (la misma observación
  es 4 en la tabla entera y 1 con `sex=male`), así que no identifica una observación y no se puede comparar entre dos
  peticiones.

!!! note "Dos personas, una imagen"
    La tabla de resultados tiene solo la clasificación **final**, así que nunca contiene las observaciones de dos
    usuarios sobre la misma imagen. Para leer lo que dijo cada usuario, usa
    [`user_classifications`](user_classifications.md).

    Trapper enlaza las clasificaciones por **linaje**, no por la posición de una observación (según su código): la
    clasificación de un usuario puede hacerse a partir de otra (la de la IA, o la de otro usuario), y la final apunta a la
    que se aprobó. Las cajas tienen un uso ahí: la tarea `CopyBboxesFromAI` copia las cajas de una clasificación de la IA
    a la del experto aprobada **cuando las dos tienen el mismo conteo total y el mismo tipo de observación y los objetos
    del experto son indistinguibles** (los mismos valores en los campos que se comparan); las cajas se reparten entonces
    entre los objetos al azar, como dice su docstring. No compara dónde están las cajas de las clasificaciones de dos
    usuarios. Para saber si dos observaciones son el mismo animal, compara tú las cajas cuando ambas las tienen (su
    solapamiento), y la especie y el conteo cuando no. *No comprobado con dos usuarios sobre una imagen: los servidores de
    prueba tienen uno, y ninguna de sus observaciones tiene cajas.*

!!! note "No confundir con la tabla de media"
    [`client.classification_media`](classification_media.md) es la tabla de los *ficheros* del proyecto; esto es *lo que
    muestran*. Se unen por `mediaID`: hay un ejemplo allí.

!!! note "Leer y luego editar"
    La API no puede crear, editar ni aprobar una clasificación: la lista es de solo lectura (`Allow: GET, HEAD, OPTIONS`
    en v1 y v2) y la única escritura es la [importación](#importar-observaciones-desde-un-csv). Para corregir
    clasificaciones con un script: exporta la tabla de resultados con **`camtrapdp=False`** (el formato que lleva `_id`,
    que la importación exige; el `camtrapdp=True` por defecto no lo lleva), edítala e impórtala.

**Endpoints:**

- `GET /media_classification/api/classifications` (listado + detalle)
- `GET /media_classification/api/classifications/results/{project_pk}/` — exportación CSV/modelos de las observaciones de un proyecto
- `POST /media_classification/api/classifications/import/` — importa observaciones desde un CSV

## Filtros

| Parámetro | Tipo | Descripción |
|---|---|---|
| `project` | PK | El proyecto de la lista. **Obligatorio para `deployment` y `collection`**: Trapper los comprueba contra los del proyecto y, sin él, contesta `400 "Select a valid choice"`. Los métodos por proyecto de más abajo lo toman de la URL |
| `owner` | booleano | `true` = recursos donde el usuario es propietario/gestor |
| `deployment` | lista de PK | PK de despliegue (necesita `project`) |
| `collection` | lista de PK | La pk del **vínculo entre el proyecto y la colección**, no la de la colección (necesita `project`; véase la entrada 51 de `TRAPPER_API_IMPROVEMENTS.md`) |
| `locations_map` | PK separadas por comas | Filtra por PK de localización |
| `rdate_from` / `rdate_to` | fecha | Rango de `date_recorded` |
| `rtime_from` / `rtime_to` | HH:MM | Rango de hora del día |
| `ftype` | opción | Tipo de recurso (IMAGE, VIDEO, ...) |
| `bboxes` | booleano | Tiene cajas delimitadoras |
| `classified`, `classified_ai` | booleano | Tiene una clasificación de un usuario / de la IA |
| `approved` | booleano | Aprobada. **Solo v2**: v1 lo ignora y llama `status` al mismo filtro |
| `status` | booleano | Aprobada, **solo en v1** (v2 lo ignora) |
| `species` | lista de PK | Filtra por PK de especie |
| `observation_type` | opción | Filtra por tipo de observación |
| `sex` | opción | Filtra por sexo |
| `age` | opción | Filtra por edad |

!!! warning "Filtros que este endpoint ignora"
    Trapper ignora un parámetro que no conoce **sin dar error**, y la lista vuelve sin filtrar. Además de los de
    arriba, `user`, `feedback`, `confidence` y `ai_provider`, que una versión anterior de esta guía listaba, no hacen
    nada aquí (comprobado en v1 y v2: `user=1` y `ai_provider=1` devuelven todas las filas; son de las listas de
    clasificaciones de usuario y de IA). Un filtro que no deja ninguna fila contesta `200` con una lista vacía, pero la
    tabla de resultados y la de media contestan `400 "Empty queryset..."`.

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
