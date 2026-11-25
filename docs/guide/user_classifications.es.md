# Clasificaciones de usuario

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — comprobado en los dos. Consulta [Versiones de Trapper](versions.md).

`client.user_classifications` — clasificaciones individuales (no finales) hechas por usuarios humanos,
antes de que se aprueben como [clasificación final](classifications.md).

**Endpoint:** `GET /media_classification/api/user-classifications` (listado + detalle).

## Filtros

Trapper ignora sin error un filtro que no aplica y devuelve todas las filas: el SDK emite un
`UnknownFilterWarning` para un nombre que la versión del servidor no aplica.

| Parámetro | Tipo | Versión | Descripción |
|---|---|---|---|
| `project` | PK | ambas | Proyecto de clasificación. **Necesario para `deployment` y `collection`** (`ValueError` sin él) |
| `deployment` | lista de PK | ambas | PK de despliegues del proyecto |
| `collection` | lista de PK | ambas | PK del **enlace** entre el proyecto y la colección |
| `user` | lista de PK | ambas | Quién clasificó (PK de usuario) |
| `owner` | booleano | ambas | `true` = las clasificaciones del propio usuario |
| `approved` | booleano | ambas | Se convirtió en la clasificación final |
| `feedback` | booleano | ambas | Es una clasificación de retroalimentación |
| `bboxes` | booleano | ambas | Tiene cajas delimitadoras |
| `ftype` | opción | ambas | Tipo de recurso (`I`, `V`, ...) |
| `species` | lista de PK | ambas | PK de especies |
| `observation_type` | opción | ambas | Tipo de observación |
| `locations_map` | PK separadas por comas | ambas | PK de localizaciones |
| `rdate_from` / `rdate_to` | fecha | ambas | Rango de `date_recorded` |
| `rtime_from` / `rtime_to` | HH:MM | ambas | Rango de hora del día |
| `search` | texto | ambas | Especie (nombre latino o inglés), nombre del recurso o atributo |
| `sex`, `age` | opción | v2 | Sexo, edad |
| `classified` / `classified_ai` | booleano | v2 | El recurso tiene una clasificación de usuario / de IA |

v2 aplica además los campos de su modelo (`is_blank`, `has_animals`, `classification_type`, ...) y un filtro por
cada atributo propio del clasificador del proyecto.

## Qué trae una fila

El recurso, las observaciones (`dynamic_attrs`: `observation_type`, `species` y `count`, como texto; una especie
ausente es `None`) y si se convirtió en la clasificación final (`approved`). v2 no envía `classification` ni
`created_at`, y añade `is_feedback`, `is_setup`, `bboxes` y `classification_project`.

## Los seis patrones de acceso

Este componente no tiene métodos especiales: es exactamente la interfaz genérica descrita en
[Uso](../usage.md):

```python
page = client.user_classifications.get(page=1, page_size=50, approved=True)
for row in client.user_classifications.where(species=42):
    print(row)
result = client.user_classifications.get_all(page_size=100)
row = client.user_classifications.find(1)
client.user_classifications.export(file="user_classifications.csv")
```
