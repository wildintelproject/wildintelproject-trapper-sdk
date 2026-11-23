# Especies

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ (aún sin validar contra un servidor Trapper v2 real). Consulta [Versiones de Trapper](versions.md).

`client.species` — la tabla de taxonomía de especies. Las PK que devuelve son las mismas que usa el
filtro `species` de los componentes relacionados con clasificaciones (p. ej.
[`classifications`](classifications.md), [`ai_classifications`](ai_classifications.md)).

**Endpoint:** `GET /tables/api/species` (listado + detalle).

## Filtros

| Parámetro | Tipo | Descripción |
|---|---|---|
| `english_name` | cadena | Filtra por nombre en inglés exacto |
| `latin_name` | cadena | Filtra por nombre latino exacto |
| `search` | cadena | Búsqueda de texto libre en `english_name` y `latin_name` |

## Los seis patrones de acceso

Este componente no tiene métodos especiales: es exactamente la interfaz genérica descrita en
[Uso](../usage.md):

```python
page = client.species.get(page=1, page_size=50)
for sp in client.species.where(search="fox"):
    print(sp)
result = client.species.get_all()
sp = client.species.find(1)
client.species.export(file="species.csv")
```
