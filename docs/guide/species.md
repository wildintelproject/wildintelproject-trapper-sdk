# Species

`client.species` — the species taxonomy table. PKs returned here are the same ones referenced by
the `species` filter on classification-related components (e.g.
[`classifications`](classifications.md), [`ai_classifications`](ai_classifications.md)).

**Endpoint:** `GET /tables/api/species` (list + detail).

## Filters

| Parameter | Type | Description |
|---|---|---|
| `english_name` | string | Filter by exact english name |
| `latin_name` | string | Filter by exact latin name |
| `search` | string | Free-text search across `english_name`, `latin_name` |

## The six access patterns

This component has no special methods — it's exactly the generic interface described in
[Usage](../usage.md):

```python
page = client.species.get(page=1, page_size=50)
for sp in client.species.where(search="fox"):
    print(sp)
result = client.species.get_all()
sp = client.species.find(1)
client.species.export(file="species.csv")
```
