# Sequences

`client.sequences` — resource sequences: events grouping resources recorded within a configurable
time interval of each other.

**Endpoint:** `GET /media_classification/api/sequences` (list + detail). This endpoint is **not
paginated** server-side — `get_all()`/`where()`/`all()` still work transparently, since the single
unpaginated response is treated as page 1 of 1.

## Filters

| Parameter | Type | Description |
|---|---|---|
| `sequence_id` | int | Filter by sequence id |
| `sequence_uuid` | str | Filter by sequence UUID |
| `interval` | int | Filter by grouping interval (seconds) |
| `collection` | PK | Filter by classification-project-collection PK |
| `deployment` | comma-separated PKs | Filter by deployment PKs of member resources |

## The six access patterns

This component has no special methods — it's exactly the generic interface described in
[Usage](../usage.md):

```python
page = client.sequences.get(page=1, page_size=50)
for seq in client.sequences.where(collection=35):
    print(seq)
result = client.sequences.get_all()
seq = client.sequences.find(1)
client.sequences.export(file="sequences.csv")
```
