# Mapa de clasificaciones

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — el mismo código en ambas. Consulta [Versiones de Trapper](versions.md).

`client.classifications_map` — recursos pendientes de clasificar de un proyecto dado, tal como los usa la
vista de mapa/cola de la interfaz de clasificación.

**Endpoint:** `GET /media_classification/api/classifications_map` (listado + detalle).

## Filtros

| Parámetro | Tipo | Descripción |
|---|---|---|
| `project` | PK | Filtra por PK de proyecto de clasificación |
| `owner` | booleano | `true` = recursos donde el usuario es propietario/gestor |
| `deployment` | lista de PK | Filtra por PK de despliegue |
| `collection` | lista de PK | Filtra por PK de colección |
| `locations_map` | PK separadas por comas | Filtra por PK de localización |
| `rdate_from` / `rdate_to` | fecha | Rango de `date_recorded` |
| `rtime_from` / `rtime_to` | HH:MM | Rango de hora del día |
| `ftype` | opción | Tipo de recurso (IMAGE, VIDEO, ...) |
| `classified` | booleano | Clasificado por humanos |
| `classified_ai` | booleano | Clasificado por IA |
| `approved` | booleano | Tiene una clasificación FINAL aprobada |
| `species` | lista de PK | Filtra por PK de especie |
| `observation_type` | opción | Filtra por tipo de observación |

## Los seis patrones de acceso

Este componente no tiene métodos especiales: es exactamente la interfaz genérica descrita en
[Uso](../usage.md):

```python
page = client.classifications_map.get(page=1, page_size=50, project=7)
for row in client.classifications_map.where(project=7, classified=False):
    print(row)
result = client.classifications_map.get_all(project=7)
row = client.classifications_map.find(1)
client.classifications_map.export(file="classifications_map.csv")
```
