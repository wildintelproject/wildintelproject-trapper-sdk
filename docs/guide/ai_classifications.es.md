# Clasificaciones de IA

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — comprobado en los dos. Consulta [Versiones de Trapper](versions.md).

`client.ai_classifications` — observaciones de clasificación producidas por un proveedor de IA.

**Endpoints:**

- `GET /media_classification/api/ai-classifications` (listado + detalle)
- `GET /media_classification/api/ai-classifications/results/{project_pk}/` — exportación CSV/modelos de un proyecto

## Filtros

| Parámetro | Tipo | Descripción |
|---|---|---|
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
