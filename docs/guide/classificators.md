# Classificators

`client.classificators` — classificator configurations (the taxonomy/attribute schema a
classification project classifies against).

**Endpoint:** `GET /media_classification/api/classificators` (list + detail).

## Filters

| Parameter | Type | Description |
|---|---|---|
| `owner` | boolean | `true` = classificators owned by the user |
| `search` | string | Search by name or description |

## The six access patterns

This component has no special methods — it's exactly the generic interface described in
[Usage](../usage.md):

```python
page = client.classificators.get(page=1, page_size=50)
for classificator in client.classificators.where(owner=True):
    print(classificator)
result = client.classificators.get_all()
classificator = client.classificators.find(1)
client.classificators.export(file="classificators.csv")
```
