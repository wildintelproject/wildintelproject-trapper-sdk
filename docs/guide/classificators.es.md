# Clasificadores

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — el mismo código en ambas. Consulta [Versiones de Trapper](versions.md).

`client.classificators` — configuraciones de clasificador (el esquema de taxonomía y atributos con el
que un proyecto de clasificación clasifica).

**Endpoint:** `GET /media_classification/api/classificators` (listado + detalle).

## Filtros

| Parámetro | Tipo | Descripción |
|---|---|---|
| `owner` | booleano | `true` = clasificadores del usuario |
| `search` | cadena | Búsqueda por nombre o descripción |

## Los seis patrones de acceso

Este componente no tiene métodos especiales: es exactamente la interfaz genérica descrita en
[Uso](../usage.md):

```python
page = client.classificators.get(page=1, page_size=50)
for classificator in client.classificators.where(owner=True):
    print(classificator)
result = client.classificators.get_all()
classificator = client.classificators.find(1)
client.classificators.export(file="classificators.csv")
```
