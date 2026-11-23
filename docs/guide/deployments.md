# Deployments

!!! info "Trapper compatibility"
    **v1** ✔ · **v2** ✔ — `import_deployments()` works on both but behaves differently (see below), and `geojson()` is **v2 only**. See [Trapper versions](versions.md).

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

!!! warning "Trapper ignores a filter it does not know"
    A parameter that is not a filter of Trapper (a typo, `colls`, `ordering`, `radius`...) is **ignored without an
    error**, and the list comes back unfiltered. The SDK knows the filters of each Trapper version and, when you
    pass another one, emits an `UnknownFilterWarning` that names it (the request is still sent). Besides those in
    the table, the list applies `pk`, `deployment_code`, `deployment_id`, `setup_by`, `camera_*`, `detection_distance`,
    `bait_type`, `feature_type`, `habitat`, `session`, `array`, `comments`, `date_created`, `managers`, `start_date`,
    `end_date`, `is_incomplete`, `view_quality`, `capture_method` and `status`, and v2 also applies `in_bbox`. To
    silence it: `warnings.simplefilter("ignore", err.UnknownFilterWarning)`.

## Filtering by area

A deployment has no coordinates of its own: they are its location's, and the deployment list gives only the
location's pk, so `where()` has no spatial filter. `in_area()` takes the same area as
[`client.locations.in_area()`](locations.md#filtering-by-area) and returns the deployments whose location is inside:

```python
# a bounding box: (min_lon, min_lat, max_lon, max_lat)
for dep in client.deployments.in_area(bbox=(-7.0, 36.5, -5.5, 37.5)):
    print(dep.deployment_id, dep.location_id)

# a circle: the centre as (longitude, latitude), the radius in metres, plus the usual filters
near = list(client.deployments.in_area(center=(-6.44, 37.05), radius=5_000, research_project=3, sdate_from="2024-01-01"))
```

It finds the locations in the area first (every location the account can see is read and filtered on the
client) and then asks for the deployments of those locations, 50 location pks per request. The other keywords are
filters of the **deployments**, not of the locations, and `location` cannot be combined with the area. A deployment
whose location has no readable coordinates is left out, and a wrong area raises `ValueError` before any request for
deployments.

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

## GeoJSON (Trapper v2 only)

`geojson()` returns the deployments as a GeoJSON `FeatureCollection`. It replaces
[`client.maps`](maps.md) and [`client.locations_geojson`](locations_geojson.md), which Trapper v2
removed; on a v1 server it raises `UnsupportedVersionError`.

```python
fc = client.deployments.geojson(classification_project=2, species=[3, 7])
for feature in fc["features"]:
    lon, lat = feature["geometry"]["coordinates"]
    print(feature["properties"]["deploymentID"], lon, lat)
```

| Parameter | Description |
|---|---|
| `classification_project` | Keep deployments linked to this classification project; scopes `observation_type` and `species` to its classifications |
| `observation_type` | One value or a list (`"animal"`, `["animal", "human"]`) |
| `species` | One species pk or a list |
| `start_date_gte`, `end_date_lte` | Deployments starting on/after, or ending on/before, a date (`YYYY-MM-DD`) |
| `refresh` | Bypass the server's one-hour cache for this query |

Only deployments the current user can access are returned.

## Fields: the list and the export

Like locations, a deployment comes in two shapes, and neither holds every field. `where()`, `get()` and `find()`
return a `Deployment` (Trapper's JSON): `pk`, `deployment_code`, `deployment_id`, `location` (the location's
**pk**), `location_id`, `start_date`, `end_date`, `owner`, `research_project` (its **acronym**), `tags`,
`correct_setup` and `correct_tstamp`. `export(file=None)` returns a `DeploymentExport` for each row of the CSV,
which has the camera and setup fields instead (`setup_by`, `camera_*`, `detection_distance`, `bait_use`,
`feature_type`, `habitat`, `session`, `array`, `comments`, `longitude`, `latitude`, `location_name`) but **not**
the owner, the research project or `correct_setup` and `correct_tstamp`. Both have `pk`, `deployment_id`,
`location_id`, `start_date`, `end_date` and `tags`. Checked on Trapper v1 and v2.

`start_date` and `end_date` are timezone-aware `datetime` objects in both shapes, although Trapper spells them
differently (`2024-01-01T00:00:00+01:00` in the JSON, `2024-01-01T00:00:00+0100` in the CSV), so they can be
compared and sorted whichever you read. A date that cannot be read is kept as the text it came as, and an empty
one is `None`. `export(file="x.csv")` writes them back as ISO text with the colon (`+01:00`); `raw=True` keeps
Trapper's own spelling.

Trapper's CSV has no column for `session`, `array`, `tags` or `bait_type`: it puts the first two in
`deploymentGroups` (`session:S | array:A`) and the tags in `deploymentTags`, with `baitType:<value>` added
when the deployment has a bait type. `DeploymentExport` reads them from there, so `tags` holds only the tags and
`bait_type` the bait. To get the CSV exactly as Trapper sends it, use `export(file=..., raw=True)`.

## Importing deployments (write access)

`/geomap/api/deployments` is read-only, so `import_deployments()` works around that by simulating
the classic web UI's `geomap/deployment/import/` form via cookie/session auth instead of the API's
token auth (see [`APIClientBase.session_login`](../api/api_client_base.md)).

On **Trapper v2** the same method posts to the import action of the Django admin
(`admin/geomap/deployment/import-deployments/`). The account must be a staff user with the add
permission, and the server imports asynchronously: `True` means the table passed validation and was
queued, so poll `client.deployments` if you need the rows to be there. Rejected tables raise
`APIError` with the server's message and the per-row errors.

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

### Waiting for the import to land

On Trapper v2 the import runs in the background: `import_deployments()` returning `True` means the
table was validated and queued, not that the rows exist yet. Neither version exposes the import
task through the API, so `wait_for_import()` checks the outcome instead — it polls until every
`deploymentID` is listed:

```python
client.deployments.import_deployments(file="deployments.csv", research_project=1, timezone="Europe/Madrid")
client.deployments.wait_for_import(["DON01-2024A", "DON01-2024B"], timeout=60)   # raises TimeoutError if missing
```

Pass `raise_on_timeout=False` to get `False` back instead. It works the same on v1.

### Updating deployments

Trapper has no endpoint to edit a deployment, but the import updates the ones that exist when it gets
`update=True` and an `_id` column with their primary keys. The CSV that Trapper exports has that column, so the
way to correct deployments is **export, edit, import**:

```python
import csv

# 1. Export the deployments exactly as Trapper sends them (raw=True keeps the _id column and the header)
path = client.deployments.export(file="deployments.csv", raw=True, research_project=7)

# 2. Edit the CSV: change the cells you want, keep the header and the _id
with open(path, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
for row in rows:
    if row["deploymentID"] == "don01-2024a":
        row["cameraHeight"] = "1.25"
        row["habitat"] = "dehesa"
with open("edited.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

# 3. Import it with update=True, and wait until the new values are there
client.deployments.import_deployments(
    file="edited.csv", research_project=7, timezone="Europe/Madrid", update=True,
)
client.deployments.wait_for_update({"don01-2024a": {"camera_height": 1.25, "habitat": "dehesa"}})
```

`import_deployments()` returns `True` when the table is validated and queued, on v1 and v2: the changes are
applied a moment later. `wait_for_import()` cannot tell, because the IDs exist already, so
`wait_for_update()` polls the export until each deployment has the values you give, with the field names of
`DeploymentExport` (numbers are compared with a tolerance). It raises `TimeoutError`, or returns `False` with
`raise_on_timeout=False`, if they do not arrive in `timeout` seconds. Give it the stored ID: Trapper slugifies
the `deploymentID` of an import (`"Don 01"` is stored as `"don-01"`). Checked on Trapper v1 and v2. As on the rest of the
imports, the account must be staff on v2.

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
