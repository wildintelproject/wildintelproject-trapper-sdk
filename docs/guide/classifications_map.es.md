# Mapa de clasificaciones

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — comprobado en los dos. Consulta [Versiones de Trapper](versions.md).

`client.classifications_map` — las clasificaciones finales en forma ligera, tal como las usa el mapa de la interfaz
de clasificación.

**Endpoint:** `GET /media_classification/api/classifications_map` (listado + detalle). Las mismas filas y filtros
que la lista de [resultados de clasificación](classifications.md) (todas las clasificaciones finales que ve el
usuario), pero:

- **Sin paginar**: una respuesta con todas las filas; `page` y `page_size` no hacen nada.
- **Menos en cada fila** (`ClassificationMap`): el recurso (su `deployment` es el `deploymentID`), el proyecto, y
  `dynamic_attrs` con **solo los atributos propios** del clasificador — sin tipo de observación, especie ni
  recuento. Para eso, `client.classification_results`.

## Filtros

Los de la lista de clasificaciones. Trapper ignora sin error cualquier otro; el SDK emite un
`UnknownFilterWarning`.

| Parámetro | Tipo | Descripción |
|---|---|---|
| `project` | PK | El proyecto. **Necesario para `deployment` y `collection`** (`ValueError` sin él) |
| `owner` | booleano | `true` = recursos de los que el usuario es propietario/gestor |
| `deployment` | lista de PK | PK de despliegues del proyecto |
| `collection` | lista de PK | PK del **enlace** entre el proyecto y la colección |
| `locations_map` | PK separadas por comas | PK de localizaciones |
| `rdate_from` / `rdate_to` | fecha | Rango de `date_recorded` |
| `rtime_from` / `rtime_to` | HH:MM | Rango de hora del día |
| `ftype` | opción | Tipo de recurso (`I`, `V`, ...) |
| `classified` / `classified_ai` | booleano | Tiene una clasificación de usuario / de IA |
| `approved` | booleano | Aprobada. Funciona en las dos versiones: v1 lo llama `status` y el SDK lo envía así |
| `bboxes` | booleano | Tiene cajas delimitadoras |
| `species` | lista de PK | PK de especies |
| `observation_type`, `sex`, `age` | opción | Tipo de observación, sexo, edad |

## Uso

```python
filas = client.classifications_map.get_all(project=7, approved=True).results
for fila in client.classifications_map.where(project=7, deployment=[3, 4]):
    print(fila.resource.name, fila.resource.deployment, fila.dynamic_attrs)
fila = client.classifications_map.find(231)
```
