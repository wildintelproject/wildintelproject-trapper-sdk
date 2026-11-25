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
| `locations_map` | list of PKs | Filter via `deployment__location` (**v1 only**: Trapper v2 ignores it) |
| `collections` | list of PKs | Filter by one or more collection PKs (any of them) |
| `deployments` | list of PKs | Filter by deployment PKs (any of them) |
| `tags` | list of PKs | Filter by tag PKs |
| `observation_type` | string | Full-text search for `observation_type:<value>` |
| `species` | list of PKs | Full-text search for `species_id:<value>` |
| `timestamp_error` | boolean | `true` = resources outside the deployment's date range |
| `search` | string | Full-text search across name and data vectors |

Lists (`pk`, `locations_map`, `collections`, `deployments`, `tags`, `species`) can be given as a list or as a
comma-separated string: `collections=[2, 3]` and `collections="2,3"` are the same. Trapper reads each one in a
different form (`deployments` and `collections` as repeated parameters, `pk` and `locations_map` as one string with
commas), and gets it wrong without telling you when given the other: `deployments="1,2"` is ignored and returns
every resource, `collections="2,3"` is a `400`, `pk=[1, 2]` keeps one pk and `locations_map=[1, 2]` finds nothing.
The SDK sends each one the way Trapper reads it.

!!! warning "A filter that Trapper does not apply"
    Trapper ignores a parameter that is not one of its filters **without an error**, and the list comes back
    unfiltered; the SDK emits an `UnknownFilterWarning` that names it (the request is still sent). Besides those in
    the table, the list applies `name`, `deployment`, `mime_type`, `file_size`, `token` and `file_checksum_hash`.
    `locations_map` is ignored by v2, and `ordering` and `in_bbox` by both. `deployment__isnull`, which an older
    version of this guide listed, makes Trapper answer **`500`** on v1 and v2, whatever the value: the SDK warns about
    it and there is no filter for the resources without a deployment. To silence the warning:
    `warnings.simplefilter("ignore", err.UnknownFilterWarning)`.

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

## Dates

`date_recorded` is a timezone-aware `datetime` (`2024-03-10T20:49:43+01:00` in Trapper's JSON), so resources can be
compared and sorted by when they were taken. One that cannot be read stays as the text it came as, and an empty one
is `None`. `export(file="x.csv")` writes it back as ISO text.

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

### Downloading all the files of a deployment or a collection

Trapper has no endpoint for it: it is `download()` once per resource. `deployments.download_resources()` and
`collections.download_resources()` do that loop, and need `user_name` and `user_password` like `download()`:

```python
report = client.deployments.download_resources(12, "downloads/")          # downloads/<deployment_id>/<name>.jpg
report = client.collections.download_resources(5, "downloads/")           # downloads/<collection name>/<name>.jpg
print(report)        # 40 downloaded, 0 already there, 0 failed, in downloads/don01-2024a
```

- **Choosing which resources.** Any filter of the resource list goes through, so the server does the choosing
  (`resource_type="I"`, `rdate_from`/`rdate_to`, `rtime_from`/`rtime_to`, `tags`, `species`, `search`, `pk=[...]`, and
  `deployments=[...]` for a collection), and `filter_fn` does it on the client for what the server cannot filter:
  `client.deployments.download_resources(12, "out/", rdate_from="2024-03-01", filter_fn=lambda r: r.date_recorded.hour < 6)`.
  The first argument is called `deployment_pk` / `collection_pk` because `pk` is one of those filters.
- **A run can be repeated.** A file that is already in the folder is skipped (`skip_existing=True`), and a file is
  only given its name when it is complete (it is a `.part` until then), so after an interruption or a failure you
  run the same call again and it carries on.
- **A failure does not stop the rest** (`on_error="continue"`): it goes in `report.failed` (`{resource pk: message}`).
  `on_error="raise"` stops at the first one. Each file is retried like `download()` does (`retry_attempts`, ...).
- **The report** (`DownloadReport`): `downloaded`, `skipped` (lists of paths), `failed`, `ok` and `total`.
- **Names.** `<name><extension>`, the extension from the resource's `mime`; `-<pk>` is added when two resources share a
  name; a file name is cleaned of characters a file system refuses. `kind="thumbnail"` or `"preview"` saves
  `<name>-thumbnail.jpg`, next to the originals. The folder of a collection is flat: the resource list does not say
  which deployment a resource belongs to.
- **Progress.** `progress_callback(event, data)` is called for every file with `"downloaded"`, `"skipped"` or `"failed"`
  and `{"resource", "path", "index", "total"}` (`"error"` too for a failure); `total` is `None` with a `filter_fn`.
- It works over the list of resources you give it, too: `client.resources.download_many(resources, "folder/")`.

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

!!! note "Paging"
    On the old routes Trapper orders the resource list by recording time, which is not unique, so its pages can
    repeat and skip rows. `where()`, `all()` and `get_all()` ask for pages of 500 (one request when the list fits)
    and drop repeated rows; a longer list emits an `UnstableOrderWarning`. On the new API it is ordered by `pk`.
