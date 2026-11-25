# Mapas

!!! warning "Solo Trapper v1"
    Eliminado en Trapper v2: en un servidor v2 lanza `UnsupportedVersionError`. Consulta [Versiones de Trapper](versions.md).

`client.maps` — mapas basados en umap accesibles para el usuario actual.

**Endpoint:** `GET /geomap/api/maps` (listado + detalle).

## Filtros

| Parámetro | Tipo | Descripción |
|---|---|---|
| `owner` | booleano | `true` = mapas del usuario actual |
| `search` | cadena | Búsqueda de texto libre en nombre, descripción y nombre de usuario del propietario |

Trapper ignora sin error cualquier otro filtro; el SDK emite un `UnknownFilterWarning`.

## Los seis patrones de acceso

Este componente no tiene métodos especiales: es exactamente la interfaz genérica descrita en
[Uso](../usage.md):

```python
page = client.maps.get(page=1, page_size=50)
for m in client.maps.where(owner=True):
    print(m)
result = client.maps.get_all()
m = client.maps.find(1)
client.maps.export(file="maps.csv")
```
