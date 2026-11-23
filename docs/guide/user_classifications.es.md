# Clasificaciones de usuario

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — el mismo código en ambas. Consulta [Versiones de Trapper](versions.md).

`client.user_classifications` — clasificaciones individuales (no finales) hechas por usuarios humanos,
antes de que se aprueben como [clasificación final](classifications.md).

**Endpoint:** `GET /media_classification/api/user-classifications` (listado + detalle).

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
| `classified` | booleano | Clasificado por humanos |
| `classified_ai` | booleano | Clasificado por IA |
| `bboxes` | booleano | Tiene cajas delimitadoras |
| `approved` | booleano | Tiene una clasificación FINAL aprobada |
| `feedback` | booleano | Es una clasificación de retroalimentación |
| `species` | lista de PK | Filtra por PK de especie |
| `observation_type` | opción | Filtra por tipo de observación |
| `sex` | opción | Filtra por sexo |
| `age` | opción | Filtra por edad |

## Los seis patrones de acceso

Este componente no tiene métodos especiales: es exactamente la interfaz genérica descrita en
[Uso](../usage.md):

```python
page = client.user_classifications.get(page=1, page_size=50, classified=True)
for row in client.user_classifications.where(species=42):
    print(row)
result = client.user_classifications.get_all(page_size=100)
row = client.user_classifications.find(1)
client.user_classifications.export(file="user_classifications.csv")
```
