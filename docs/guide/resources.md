# Resources

!!! info "Trapper compatibility"
    **v1** ✔ · **v2** ✔ — same code on both. See [Trapper versions](versions.md).

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

## Downloading the file

The REST API lists resources but does not serve their files: `url` and `url_original` are paths of a classic web
view (`/storage/resource/media/<pk>/file/`) that **does not accept the API token**. With a token, or with no
login, it answers `404`, and it does so both when the file does not exist and when the account may not see it.
`download()` logs in with `user_name` and `user_password` (the account's *email* on servers that log in by email),
like the imports do, and saves the file:

```python
client = TrapperClient(base_url=..., access_token=..., user_name="me@example.org", user_password="...")

path = client.resources.download(29, "images/")                          # a directory: saved as 29-original.jpg
path = client.resources.download(29, "photo.jpg")                        # or a file name
thumb = client.resources.download(29, "thumb.jpg", kind="thumbnail")     # "original", "preview" or "thumbnail"

for res in client.resources.where_by_collection(5):
    client.resources.download(res.pk, "collection-5/")
```

- The file is streamed to disk, into a temporary `.part` file that is moved into place when it is complete, so a
  failure never leaves a half-written file.
- Network failures and `502`/`503`/`504` answers are retried with exponential backoff (tenacity): `retry_attempts`
  (3, the first try included; `1` disables it), `retry_min_wait` and `retry_max_wait`. A download that was cut is
  started again from the beginning. A `404` and any other answer are not retried.
- A `404` raises `NotFoundError` saying it can be the file or the permission. A preview or a thumbnail may not exist
  if Trapper did not generate them.
- `download()` raises `ValueError` if the client has no `user_name`/`user_password`.
- A Trapper that is not behind the proxy that serves its files (a development server on its own port) answers `200`
  with an empty body and an `X-Accel-Redirect` header; `download()` raises `APIError` saying so instead of saving
  an empty file. Checked on Trapper v2 (the original JPEG); on v1 only against such a server.

!!! warning "Not a stable API contract"
    It depends on an unversioned web view, like the imports.

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
