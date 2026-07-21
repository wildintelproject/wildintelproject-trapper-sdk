# Collections

`client.collections` — storage collections: groups of resources uploaded together.

**Endpoints:**

- `GET /storage/api/collections` (list + detail)
- `GET /storage/api/collections_ondemand` — on-demand collections for the current user
- `GET /storage/api/collections_map` — collections list for map rendering
- `GET /storage/api/collections_append` — collections the user can append resources to
- `POST /storage/api/collection/process/` — trigger processing of an FTP-uploaded collection

## Filters

| Parameter | Type | Description |
|---|---|---|
| `pk` | comma-separated PKs | Filter by specific collection PKs |
| `status` | choice | Filter by collection status |
| `owner` | boolean | `true` = only collections owned/managed by current user |
| `owners` | list of PKs | Filter by one or more owner user PKs |
| `research_projects` | list of PKs | Filter by one or more research project PKs |
| `locations_map` | comma-separated PKs | Filter via `resources__deployment__location` |
| `search` | string | Full-text search across `name` and owner username |

## The six access patterns

```python
# Lazy iteration (all() is the same thing)
for col in client.collections.where():
    print(col)
for col in client.collections.where(owner=True):
    print(col)
for col in client.collections.where(research_projects=3):
    print(col)

# One page
page = client.collections.get(page=1, page_size=25)
print(page.pagination.count)

# Single item
col = client.collections.find(42)
```

See [Usage](../usage.md) if any of this looks unfamiliar — it's the same interface on every component.

!!! note "Resources inside a collection"
    `CollectionsComponent` only lists *collections themselves* — for the resources inside one, use
    [`client.resources.where_by_collection(collection_pk=...)`](resources.md#scoped-to-a-collection-or-a-location).

## On-demand / map / append sub-endpoints

Three related endpoints get the exact same `where_*`/`get_*`/`get_all_*`/`find_*` set as the main
one, just scoped to a different collection subset:

```python
# On-demand collections for the current user
for col in client.collections.where_ondemand():
    print(col)
page = client.collections.get_ondemand(page_size=25)
result = client.collections.get_all_ondemand()
col = client.collections.find_ondemand(42)

# Collections for map rendering
for col in client.collections.where_map():
    print(col)

# Collections the user can append resources to
for col in client.collections.where_append():
    print(col)
```

## Triggering FTP-uploaded collection processing

```python
client.collections.trigger_collection(
    payload={
        "yaml_file": "package_123.yaml",
        "zip_file": "package_123.zip",
        "remove_zip": False,
    },
)
```
