# Clasificaciones de IA

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — comprobado en los dos. Consulta [Versiones de Trapper](versions.md).

`client.ai_classifications` — observaciones de clasificación producidas por un proveedor de IA.

**Endpoints:**

- `GET /media_classification/api/ai-classifications` (listado + detalle)
- `GET /media_classification/api/ai-classifications/results/{project_pk}/` — exportación CSV/modelos de un proyecto

## Filtros

Los mismos filtros para la lista y para la tabla de resultados de IA (`export()`). Trapper ignora sin error un
filtro que no aplica y devuelve todas las filas: el SDK emite un `UnknownFilterWarning`.

| Parámetro | Tipo | Versión | Descripción |
|---|---|---|---|
| `project` | PK | ambas | Proyecto de clasificación. **Necesario para `deployment` y `collection`** en la lista (`ValueError` sin él) |
| `deployment` | lista de PK | ambas | PK de despliegues del proyecto |
| `collection` | lista de PK | ambas | PK del **enlace** entre el proyecto y la colección |
| `ai_provider` | lista de PK | ambas | PK de proveedores (modelos) de IA |
| `confidence` | número 0-1 | ambas | Alguna observación tiene al menos esta confianza |
| `approved` | booleano | ambas | Se convirtió en la clasificación final. **v2: la tabla responde 500** (el SDK avisa) |
| `bboxes` | booleano | ambas | Tiene cajas delimitadoras |
| `ftype` | opción | ambas | Tipo de recurso (`I`, `V`, ...) |
| `species` | lista de PK | ambas | PK de especies |
| `observation_type` | opción | ambas | Tipo de observación |
| `search` | texto | ambas | Especie (nombre latino o inglés), nombre del recurso o atributo (lista) |
| `owner`, `user`, `feedback` | | v2 | Como en la [lista de usuarios](user_classifications.md) |
| `locations_map`, `rdate_from`/`rdate_to`, `rtime_from`/`rtime_to` | | v2 | Localización, fecha y hora del recurso |
| `sex`, `age`, `classified`, `classified_ai` | | v2 | Como en la lista de usuarios |

v1 aplica además un filtro por cada atributo propio del clasificador del proyecto, cuando se da `project`.

## Los seis patrones de acceso

```python
page = client.ai_classifications.get(page=1, page_size=50, ai_provider=1)
for row in client.ai_classifications.where(species=42):
    print(row)
result = client.ai_classifications.get_all(page_size=100)
row = client.ai_classifications.find(1)
```

Consulta [Uso](../usage.md) si algo de esto te resulta desconocido: es la misma interfaz en todos los componentes.

## Qué trae una fila en cada versión

La lista se lee igual en las dos versiones, pero v2 envía menos: no trae `owner`, `owner_profile`,
`classification` ni `created_at` (quedan a `None`), y `updated_at` puede ser `None`. v2 añade `is_setup`, `bboxes`
y `classification_project`.

Cada observación de `dynamic_attrs` tiene `observation_type`, `species`, `count` y `classification_confidence`
como texto, igual que los envía v1. La confianza es una fracción (`"0.93"`) en las dos versiones —v2 la envía como
porcentaje junto al valor y el SDK la convierte—, la misma escala que el filtro `confidence` (`confidence=0.9`).
Una especie ausente, que Trapper escribe como el texto `"None"`, es `None`.

## Exportación, limitada a un proyecto

A diferencia de los demás componentes, aquí `export()` tiene una **firma distinta**: exige un
`classification_project_pk` (el endpoint subyacente lo necesita y no existe exportación sin proyecto):

```python
client.ai_classifications.export(
    classification_project_pk=7,
    file="ai_results.csv",
)

# O recibir instancias de modelo en lugar de un fichero
records = client.ai_classifications.export(classification_project_pk=7, file=None)
```

Es una tabla con una fila por observación, con las mismas columnas que la
[tabla de resultados](classifications.md) de `client.classification_results`, y se lee igual: filas
`AIClassificationRecordExportCamTrap` por defecto y filas `AIClassificationRecordExportTrapper` (con `_id` y las
cajas en `bboxes`) con `camtrapdp=False`. Un proyecto sin clasificaciones de IA, o sin ninguna que cumpla los
filtros, no da filas (`[]`, o un fichero vacío) en lugar del `400 "Empty queryset"` de Trapper.

`raw=True` (o `validate=False`, como antes) guarda el CSV tal como lo envía Trapper.

Campo adicional en el endpoint de exportación:

| Parámetro | Tipo | Por defecto | Descripción |
|---|---|---|---|
| `camtrapdp` | booleano | `True` | `True` = filas en el estándar CamtrapDP, `False` = formato interno de Trapper |
