# Deployments

`client.deployments` — camera deployments at a location, over a time range.

**Endpoints:** `GET /geomap/api/deployments` (list + detail), `GET /geomap/api/deployments/export/` (CSV export).

The REST API is otherwise read-only for this resource; see [Importing deployments](#importing-deployments-write-access)
below for the one write operation this component supports.

## Filters

| Parameter | Type | Description |
|---|---|---|
| `location` | int or list | Filter by location ID(s) |
| `research_project` | int or list | Filter by research project ID(s) |
| `tags` | int or list | Filter by tag ID(s) |
| `owner` | bool | Filter by current user ownership |
| `sdate_from`, `sdate_to` | date (ISO) | Filter by start date range |
| `edate_from`, `edate_to` | date (ISO) | Filter by end date range |
| `classification_project` | int | Filter by classification project ID |
| `correct_setup` | bool | Filter by setup correctness |
| `correct_tstamp` | bool | Filter by timestamp correctness |
| `search` | str | Search in `deployment_id` or owner username |

## The six access patterns

```python
# One page
page = client.deployments.get(page=1, page_size=25, research_project=3)

# Every page merged
result = client.deployments.get_all(page_size=100)

# Lazy iteration (all() is the same thing)
for dep in client.deployments.where(location=42, sdate_from="2024-01-01"):
    print(dep)
for dep in client.deployments.all():
    print(dep)

# Single item
dep = client.deployments.find(99)

# CSV export
client.deployments.export(file="deployments.csv")
```

See [Usage](../usage.md) if any of this looks unfamiliar — it's the same interface on every component.

There is no collection filter: Trapper's deployment API has none, and it silently ignores any
parameter it doesn't know (such as `colls`), returning every deployment instead. Use the shortcut
below.

## Shortcut: by collection

`by_collection()` returns the deployments with at least one resource in a collection. The
deployment API can't filter by collection, but the resource API can filter by collection **and**
deployment at once: every candidate deployment — whatever `where()` returns for the filters you
pass — is checked with one single-item resource request, `max_workers` (8 by default) in parallel.
Narrow the candidates, usually with `research_project`: with no filter, every deployment on the
server is checked.

```python
# Deployments of research project 3 with images in collection 5
for dep in client.deployments.by_collection(5, research_project=3):
    print(dep)

# ...with how many images each one has there
for dep, count in client.deployments.by_collection_with_counts(5, research_project=3):
    print(dep.deployment_id, count)

# Export them to CSV
client.deployments.export_by_collection(5, research_project=3, file="deps.csv")
```

`collection_id` is the storage collection's own pk — `collection_pk` in a classification project's
collection list (`classification_projects.get_all_project_collections()`).

## Importing deployments (write access)

`/geomap/api/deployments` is read-only, so `import_deployments()` works around that by simulating
the classic web UI's `geomap/deployment/import/` form via cookie/session auth instead of the API's
token auth (see [`APIClientBase.session_login`](../api/api_client_base.md)).

!!! warning "Not a stable API contract"
    Same caveat as [locations import](locations.md#importing-locations-write-access): this depends
    on an unversioned HTML form and requires `user_name`/`user_password` (account *email*). See the
    method's docstring for the full warning.

Unlike locations, `timezone` is **required** here — the server form has no default. `research_project`
is also required (same reason as for [locations](locations.md#importing-locations-write-access): the
field is declared `required=False` but its `clean_research_project()` rejects a missing value):

```python
client.deployments.import_deployments(
    file="deployments.csv",
    timezone="Europe/Madrid",           # required
    research_project=7,                 # required
    classification_project=3,           # optional, links all imported deployments to it
    create_locations=True,              # requires locationID/longitude/latitude columns in the CSV
    update=False,                       # True updates existing deployments (requires an _id column)
)
```

There's also a ready-to-run script: [`examples/import_deployments.py`](https://github.com/wildintelproject/wildintelproject-trapper-sdk/blob/refactor/examples/import_deployments.py).

### What you get in the exception when the CSV itself is rejected

Same as [locations](locations.md#what-you-get-in-the-exception-when-the-csv-itself-is-rejected):
if the CSV fails the server's table validation (wrong/missing columns, a `deploymentID`/`locationID`
that already exists, ...), the raised `err.APIError` includes the actual per-row messages parsed out
of the server's embedded validation report, e.g.:

```
Deployment import failed (status 200): locationID 'dona-001' already exists
```

### Uploading a very large CSV: `split`

Same mechanism as [locations](locations.md#uploading-a-very-large-csv-split): there's no
chunked/resumable upload protocol on this endpoint, so `split=True` breaks the CSV into several
smaller, self-contained chunks (each repeating the header row) and imports them one request at a
time, sleeping `delay` seconds (default `1`) between uploads:

```python
client.deployments.import_deployments(
    file="huge_deployments.csv",
    timezone="Europe/Madrid",
    research_project=7,
    split=True,
    delay=2,
    chunk_size=512 * 1024,  # bytes per chunk — this is also the default
)
```

!!! warning "`split` + `create_locations=True`"
    Each chunk is imported as an independent request, so if the same `locationID` appears in more
    than one chunk, the server will try to create that location again in every chunk that
    references it — it has no memory of locations created by a previous chunk. Only combine
    `split` with `create_locations=True` if you know each `locationID` falls within a single
    chunk, or pre-create the locations separately and import with `create_locations=False` instead.

With `raise_on_error=True` (the default), the whole call raises as soon as one chunk fails, without
uploading the rest; with `raise_on_error=False` it uploads every chunk regardless and returns
`False` if any of them failed.

### Retrying a chunk that times out: `retry_attempts`

Same mechanism as [locations](locations.md#retrying-a-chunk-that-times-out-retry_attempts): a
network-level timeout on an oversized/slow chunk is retried automatically (tenacity, exponential
backoff) via `retry_attempts`/`retry_min_wait`/`retry_max_wait` — never an HTTP error response,
which is a validation failure a retry can't fix. Set `retry_attempts=1` to disable retrying.
