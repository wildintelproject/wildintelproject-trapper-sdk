# Resources

`client.resources` — individual media files (images/videos) recorded at a deployment.

**Endpoints:**

- `GET /storage/api/resources` (list + detail)
- `GET /storage/api/resources/collection/{collection_pk}` (scoped to a collection)
- `GET /storage/api/resources/location/{location_pk}` (scoped to a location)

## Filters

| Parameter | Type | Description |
|---|---|---|
| `pk` | comma-separated PKs | Filter by specific resource PKs |
| `resource_type` | choice | Filter by resource type |
| `status` | choice | Filter by resource status |
| `rdate_from`, `rdate_to` | date | `date_recorded` range |
| `udate_from`, `udate_to` | date | `date_uploaded` range |
| `rtime_from`, `rtime_to` | HH:MM | Time-of-day range on `date_recorded` |
| `owner` | boolean | `true` = only resources owned/managed by current user |
| `locations_map` | comma-separated PKs | Filter via `deployment__location` |
| `collections` | list of PKs | Filter by one or more collection PKs |
| `deployments` | repeatable PKs | Filter by deployment PKs |
| `deployment__isnull` | boolean | `true` = resources with no deployment |
| `tags` | list of PKs | Filter by tag PKs |
| `observation_type` | string | Full-text search for `observation_type:<value>` |
| `species` | repeatable | Full-text search for `species_id:<value>` |
| `timestamp_error` | boolean | `true` = resources outside the deployment's date range |
| `search` | string | Full-text search across name and data vectors |

## The six access patterns

```python
# Lazy iteration with filters (all() is the same thing)
for res in client.resources.where(status="Public", deployments=12):
    print(res)

# One page
page = client.resources.get(page=1, page_size=100, resource_type="I")

# Single item
item = client.resources.find(123)

# CSV export
client.resources.export(file="resources.csv", status="Public")
```

See [Usage](../usage.md) if any of this looks unfamiliar — it's the same interface on every component.

## Scoped to a collection or a location

Every access pattern has a `_by_collection`/`_by_location` counterpart, hitting
`/storage/api/resources/collection/{collection_pk}` or `/storage/api/resources/location/{location_pk}`
instead of the unscoped endpoint:

```python
# All resources by collection (lazy)
for res in client.resources.where_by_collection(collection_pk=5):
    print(res)

page = client.resources.get_by_collection(collection_pk=5, page=2, page_size=25)
result = client.resources.get_all_by_collection(collection_pk=5)
res = client.resources.find_by_collection(collection_pk=5, resource_pk=123)

# All resources by location (lazy)
for res in client.resources.where_by_location(location_pk=42):
    print(res)

page = client.resources.get_by_location(location_pk=42, page_size=10)
result = client.resources.get_all_by_location(location_pk=42)
res = client.resources.find_by_location(location_pk=42, resource_pk=99)
```

This is also how you list resources within a [collection](collections.md) — `CollectionsComponent`
itself only lists *collections*, not the resources inside one.
