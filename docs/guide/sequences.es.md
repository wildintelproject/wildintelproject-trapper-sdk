# Secuencias

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — el mismo código en ambas. Consulta [Versiones de Trapper](versions.md).

`client.sequences` — secuencias de recursos: eventos que agrupan recursos registrados dentro de un
intervalo de tiempo configurable entre sí.

**Endpoint:** `GET /media_classification/api/sequences` (listado + detalle). Este endpoint **no está
paginado** en el servidor: `get_all()`/`where()`/`all()` siguen funcionando de forma transparente,
porque la única respuesta sin paginar se trata como la página 1 de 1.

## Filtros

| Parámetro | Tipo | Descripción |
|---|---|---|
| `sequence_id` | int | Filtra por id de secuencia |
| `sequence_uuid` | str | Filtra por UUID de secuencia |
| `interval` | int | Filtra por intervalo de agrupación (segundos) |
| `collection` | PK | Filtra por PK de colección de proyecto de clasificación |
| `deployment` | PK separadas por comas | Filtra por PK de despliegue de los recursos miembros |

## Los seis patrones de acceso

Este componente no tiene métodos especiales: es exactamente la interfaz genérica descrita en
[Uso](../usage.md):

```python
page = client.sequences.get(page=1, page_size=50)
for seq in client.sequences.where(collection=35):
    print(seq)
result = client.sequences.get_all()
seq = client.sequences.find(1)
client.sequences.export(file="sequences.csv")
```
