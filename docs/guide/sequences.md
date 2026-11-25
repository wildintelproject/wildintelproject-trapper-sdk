# Sequences

!!! info "Trapper compatibility"
    **v1** ✔ · **v2** ✔ — checked against both. See [Trapper versions](versions.md).

`client.sequences` — groups of resources recorded within `interval` seconds of each other in a collection of a
classification project: the events of Camtrap DP (`eventID`). Trapper builds them in the classification UI; the API
only reads them.

**Endpoint:** `GET /media_classification/api/sequences` (list + detail):

- **Not paginated**: one answer with every row (`page`/`page_size` do nothing); `get_all()`/`where()` work.
- **Not limited to what the user can see**: every sequence of the server.

A row (`Sequence`) has `sequence_id` (its number inside the collection), `sequence_uuid` (the `eventID`), `resources`
(the resource PKs — Trapper v2 repeats a resource once per classification of it; the SDK keeps one) and `created_at`.

## Filters

Trapper ignores any other filter without an error; the SDK emits an `UnknownFilterWarning`.

| Parameter | Type | Description |
|---|---|---|
| `sequence_id` | int | Number of the sequence inside its collection |
| `sequence_uuid` | str | UUID (the `eventID`) |
| `interval` | int | Grouping interval in seconds |
| `collection` | PK | PK of the **link** between the classification project and the collection |
| `deployment` | list of PKs | Deployments of its resources. A list, a tuple or `"9,3"`: the SDK sends it comma-separated, the only way Trapper reads more than one |
| `pk` | PK | The sequence |

`search` answers `500` (Trapper searches a `name` that sequences do not have): the SDK warns.

## Usage

```python
for seq in client.sequences.where(collection=3, deployment=[9, 3]):
    print(seq.sequence_uuid, seq.resources)
seq = client.sequences.find(1)
client.sequences.export(file="sequences.csv")
```
