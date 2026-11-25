# Secuencias

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — comprobado en los dos. Consulta [Versiones de Trapper](versions.md).

`client.sequences` — grupos de recursos grabados con menos de `interval` segundos de diferencia en una colección de
un proyecto de clasificación: los eventos de Camtrap DP (`eventID`). Trapper los construye en la interfaz de
clasificación; la API solo los lee.

**Endpoint:** `GET /media_classification/api/sequences` (listado + detalle):

- **Sin paginar**: una respuesta con todas las filas (`page`/`page_size` no hacen nada); `get_all()`/`where()`
  funcionan.
- **Sin limitarse a lo que ve el usuario**: todas las secuencias del servidor.

Una fila (`Sequence`) tiene `sequence_id` (su número dentro de la colección), `sequence_uuid` (el `eventID`),
`resources` (las PK de los recursos — Trapper v2 repite un recurso una vez por cada clasificación suya; el SDK deja
una) y `created_at`.

## Filtros

Trapper ignora sin error cualquier otro filtro; el SDK emite un `UnknownFilterWarning`.

| Parámetro | Tipo | Descripción |
|---|---|---|
| `sequence_id` | int | Número de la secuencia dentro de su colección |
| `sequence_uuid` | str | UUID (el `eventID`) |
| `interval` | int | Intervalo de agrupación en segundos |
| `collection` | PK | PK del **enlace** entre el proyecto de clasificación y la colección |
| `deployment` | lista de PK | Despliegues de sus recursos. Una lista, una tupla o `"9,3"`: el SDK lo envía separado por comas, la única forma en que Trapper lee más de uno |
| `pk` | PK | La secuencia |

`search` responde `500` (Trapper busca un `name` que las secuencias no tienen): el SDK avisa.

## Uso

```python
for seq in client.sequences.where(collection=3, deployment=[9, 3]):
    print(seq.sequence_uuid, seq.resources)
seq = client.sequences.find(1)
client.sequences.export(file="secuencias.csv")
```
