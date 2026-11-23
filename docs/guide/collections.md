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

What each one gives (checked on Trapper v1 and v2):

| Method | Fields | Pagination | v2 |
|---|---|---|---|
| main (`where()`, `get()`, ...) | the nine of `Collection` | paginated | yes |
| `*_ondemand` | the same nine | paginated | **no**: `UnsupportedVersionError` (Trapper answers `404`) |
| `*_map` | the same nine | **none**: Trapper returns one plain list and ignores `page_size` | yes |
| `*_append` | only `pk` and `name` (the other fields are `None`) | **none**: one plain list | yes |

The SDK wraps a plain list as a single page, so `get_map()` and `get_all_append()` work like the others and
`pagination.count` is the length of the list. `delete_data`, `update_data`, `detail_data` and `owner_profile` are web
page URLs on v1 and `None` on v2.

## Triggering FTP-uploaded collection processing

`trigger_collection()` starts the processing of a data package (a YAML definition and a ZIP) that is **already in
the account's own folder on the server**: it does not upload anything (see the uploader for that).

```python
response = client.collections.trigger_collection(
    payload={
        "yaml_file": "package_123.yaml",
        "zip_file": "package_123.zip",
        "remove_zip": False,
    },
)
print(response.json()["data"]["task_id"])
```

`yaml_file` and `zip_file` are required; `remove_zip` (default `False`), `extract_metadata` (default `False`) and
`trigger_ai_pipeline` (default `True`) are optional. Trapper checks the YAML definition and starts a background
task (it runs in the request itself only if the server has Celery off), so a `200` means it was **started**, not that
the collection exists. The answer is
`{"data": {"message": ..., "errors": ..., "task_id": ...}}`. A missing name or an invalid YAML is a `BadRequestError`
(the problems are in `data.errors`), and a file that is not in the account's folder is a `NotFoundError`; with
`raise_on_error=False` the raw response is returned instead.
