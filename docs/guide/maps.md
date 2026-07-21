# Maps

`client.maps` — umap-based maps accessible to the current user.

**Endpoint:** `GET /geomap/api/maps` (list + detail).

## Filters

| Parameter | Type | Description |
|---|---|---|
| `owner` | boolean | `true` = maps owned by the current user |
| `search` | string | Free-text search across name, description, owner username |

## The six access patterns

This component has no special methods — it's exactly the generic interface described in
[Usage](../usage.md):

```python
page = client.maps.get(page=1, page_size=50)
for m in client.maps.where(owner=True):
    print(m)
result = client.maps.get_all()
m = client.maps.find(1)
client.maps.export(file="maps.csv")
```
