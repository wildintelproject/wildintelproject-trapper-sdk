# Collections

!!! info "Trapper compatibility"
    **v1** ✔ · **v2** ✔ — except the `*_ondemand` methods, which are **v1 only** (`UnsupportedVersionError` on v2). See [Trapper versions](versions.md).

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
| `pk` | list of PKs | Filter by specific collection PKs |
| `status` | choice | `Private`, `OnDemand`, `Public` or `Archived` ([`CollectionStatus`](#filtering-by-status)), in any case |
| `owner` | boolean | `true` = only collections owned/managed by current user |
| `owners` | list of PKs | Filter by one or more owner user PKs |
| `research_projects` | list of PKs | Filter by one or more research project PKs |
| `locations_map` | list of PKs | Filter via `resources__deployment__location` (**v1 only**: Trapper v2 ignores it) |
| `search` | string | Full-text search across `name` and owner username |

Lists (`pk`, `owners`, `research_projects`, `locations_map`) can be given as a list or as a comma-separated string:
`pk=[2, 1]` and `pk="2,1"` are the same. Trapper reads `pk` and `locations_map` as one string with commas and
`owners` and `research_projects` as repeated parameters, and `pk=[2, 1]` sent the other way keeps **one** pk; the SDK
sends each one the way Trapper reads it.

### Filtering by status

Trapper compares `status` as it is stored, in upper and lower case, and a value that does not exist is an **empty
result, not an error**: `status="private"` and `status="Bogus"` both give no collections. The SDK resolves it with
`CollectionStatus` (`Private`, `OnDemand`, `Public`, `Archived`), accepting any case, the label (`"On demand"`) or the
member, and raises a `ValueError` listing the valid ones before any request when it is none of them:

```python
from trapper_client import CollectionStatus

client.collections.where(status="public")                    # the same as "Public"
client.collections.where(status=CollectionStatus.ON_DEMAND)
client.collections.where(status="Bogus")                     # ValueError: use one of Private, OnDemand, Public, Archived
```

!!! warning "A filter that Trapper does not apply"
    Trapper ignores a parameter that is not one of its filters **without an error**, and the list comes back
    unfiltered; the SDK emits an `UnknownFilterWarning` that names it (the request is still sent). Besides those in
    the table, the list applies `name`, `period_begin`, `period_end`, `is_complete_cs_collection`, `cs_deployment`,
    `managers` and `members`. `locations_map` is ignored by v2, and `description`, `date_created` and `ordering` by
    both. To silence it: `warnings.simplefilter("ignore", err.UnknownFilterWarning)`.

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
