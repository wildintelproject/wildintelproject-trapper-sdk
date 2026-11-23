# Locations

!!! info "Trapper compatibility"
    **v1** ✔ · **v2** ✔ — `import_locations()` works on both but behaves differently (see below). See [Trapper versions](versions.md).

`client.locations` — read/write access to camera-trap locations.

**Endpoint:** `GET /geomap/api/locations` (list + detail), `GET /geomap/api/locations/export/` (CSV export).

The REST API is otherwise read-only for this resource; see [Importing locations](#importing-locations-write-access)
below for the one write operation this component supports.

## Filters

| Parameter | Type | Description |
|---|---|---|
| `name` | string | Partial, case-insensitive match on location name |
| `description` | string | Partial, case-insensitive match on description |
| `owner` | boolean | `true` = only locations owned by the current user |
| `owners` | list of PKs | Filter by one or more owner user PKs |
| `research_project` | list of PKs | Filter by one or more research projects |
| `locations_map` | list of PKs | Filter by locations associated to a map |
| `deployments` | list of PKs | Filter locations that have those deployments |
| `search` | string | Global text search across `location_id`, `name`, `description`, `county`, `city`, owner username |

!!! warning "Trapper ignores a filter it does not know"
    A parameter that is not in this table, or that a typo turned into another name, is **ignored without an
    error**, and the list comes back unfiltered. The SDK knows the filters of each Trapper version and, when
    you pass another one, emits an `UnknownFilterWarning` that names it (the request is still sent). Besides
    those in the table, the list applies `pk`, `location_id`, `is_public`, `ignore_DST`, `coordinate_uncertainty`,
    `date_created`, `managers` and `research_projects_member` on both versions, and `country`, `state`, `county`
    and `city` on v1 only (`locations_map` also on v1 only). `in_bbox` is applied by v2 only; `radius` and
    `ordering` by neither. To silence it: `warnings.simplefilter("ignore", err.UnknownFilterWarning)`.

## The six access patterns

```python
# One page
page = client.locations.get(page=1, page_size=25)

# Every page merged
result = client.locations.get_all(page_size=100)

# Lazy iteration (all() is the same thing, use whichever reads better)
for loc in client.locations.where(research_project=1):
    print(loc)
for loc in client.locations.all():
    print(loc)

# By owner and free text
for loc in client.locations.where(owner=True, search="camera"):
    print(loc)

# Single item
loc = client.locations.find(42)

# CSV export (also accepts filters)
client.locations.export(file="locations.csv")
client.locations.export(query={"research_project": 5}, file="project5_locations.csv")
```

See [Usage](../usage.md) if any of this looks unfamiliar — it's the same interface on every component.

## Coordinates

Trapper returns the coordinates of a location as one string, with the **longitude first**
(`"-6.44, 37.05"`), in v1 and v2. `Location.coordinates` keeps it as it comes, and `longitude` and
`latitude` give it as numbers:

```python
loc = client.locations.find(16)
loc.coordinates         # "-6.44, 37.05"
loc.longitude           # -6.44
loc.latitude            # 37.05
```

They are `None` when the coordinates are missing, cannot be read or are out of range (longitude beyond
±180, latitude beyond ±90): one odd location does not break a listing. They are read from `coordinates` each
time, not fields of the model, so `model_dump()` does not change. The rows of `export(file=None)` carry
`longitude` and `latitude` already.

## Filtering by area

Trapper's location list has no usable spatial filter. **Trapper v1** ignores `in_bbox` and `radius` without an
error and returns every location (the GeoJSON endpoint applies them, but only on v1); **v2** applies `in_bbox`
but ignores `radius`. `in_area()` filters on the client instead, with the [coordinates](#coordinates) as
numbers, so it works the same on both:

```python
# a bounding box: (min_lon, min_lat, max_lon, max_lat)
for loc in client.locations.in_area(bbox=(-7.0, 36.5, -5.5, 37.5)):
    print(loc.name, loc.longitude, loc.latitude)

# a circle: the centre as (longitude, latitude), the radius in metres, plus the usual filters
near = list(client.locations.in_area(center=(-6.44, 37.05), radius=5_000, research_project=3))
```

Give a box, a circle or both (a location must then be inside both). The edges of the box are inside, a box
with `min_lon` greater than `max_lon` crosses the antimeridian (±180°), and the distances are great-circle
(haversine) ones. Any other keyword is an ordinary filter of the list, sent to the server, so it narrows down
what has to be read. A wrong area (nothing given, `center` without `radius`, out of range) raises
`ValueError` before any request.

!!! warning "It reads every page"
    The server cannot do all the filtering, so `in_area()` reads the locations that match the other filters and
    keeps the ones in the area. On v2 a box is also sent to the server (`in_bbox`), and only the locations in it
    are read, unless it crosses the antimeridian; on v1, and for a circle alone, every page is read. On a server with many locations, pass `research_project` or `owner`. A location
    whose coordinates cannot be read is left out.

## Fields: the list and the export

Trapper gives a location in two shapes, and **neither holds every field**. `where()`, `get()` and `find()`
return a `Location`, built from Trapper's JSON; `export(file=None)` returns a `LocationExport` for each row of
its CSV. Checked on Trapper v1 and v2:

| Field | `Location` (`find()`, `get()`, `where()`) | `LocationExport` (`export(file=None)`) |
|---|---|---|
| `pk`, `location_id`, `description`, `timezone` | yes | yes |
| `name`, `owner`, `owner_profile`, `is_public`, `date_created` | **yes** | no |
| `city`, `county`, `state` | **yes** (not on v2) | no |
| `country` | yes (not on v2) | **yes** |
| Coordinates | `coordinates`, a string, and `longitude` and `latitude` read from it | `longitude` and `latitude` |
| Research project | `research_project`, its **acronym** | `research_project_id`, its **primary key** |
| `ignore_dst` | no | **yes** |
| `habitat` | no | **yes** |
| `coordinate_uncertainty`, `managers` | no | no |

To save the export as Trapper sends it, with its own header (`locationID`, `ignoreDST`, `_id`,
`researchProject`, ...) instead of the SDK's column names, use `client.locations.export(file="locations.csv",
raw=True)`.

So to read the `ignore_dst` of a location, or the primary key of its research project, use the export; to
read its name or its owner, use the list. `coordinate_uncertainty` and `managers` exist in Trapper but are
in neither, and cannot be read. When you need both, join them by `pk`; give the export the same filters as
the list so that both return the same locations:

```python
filters = {"research_project": 3}
by_pk = {row.pk: row for row in client.locations.export(query=filters, file=None)}

for loc in client.locations.where(**filters):
    row = by_pk.get(loc.pk)
    print(loc.name, loc.longitude, row.ignore_dst, row.research_project_id)
```

Trapper builds each shape from its own serializer, with its own list of fields, which is why they differ
(entry 23 of `TRAPPER_API_IMPROVEMENTS.md`).

## Importing locations (write access)

`/geomap/api/locations` is read-only, so `import_locations()` works around that by simulating the
classic web UI's `geomap/location/import/` form via cookie/session auth instead of the API's token
auth (see [`APIClientBase.session_login`](../api/api_client_base.md)).

On **Trapper v2** the same method posts to the import action of the Django admin
(`admin/geomap/location/import-locations/`). The account must be a staff user with the add
permission, and the server imports asynchronously: `True` means the table passed validation and was
queued. Rejected tables raise `APIError` with the server's message and the per-row errors.

!!! warning "Not a stable API contract"
    This depends on an unversioned HTML form, not a documented endpoint — a Trapper change to that
    page can break it silently. It requires `user_name`/`user_password` (the account's *email*
    address on servers with `ACCOUNT_LOGIN_METHODS = {"email"}`) — a token alone cannot
    authenticate it. See the full caveat in the method's docstring before relying on it.

```python
client.locations.import_locations(
    file="locations.csv",
    research_project=7,       # required — see note below
    timezone="Europe/Madrid", # required — see note below
)
```

!!! note "`research_project` and `timezone` are required, despite the server's fields saying otherwise"
    The server's `LocationImportForm` declares both fields `required=False`, but:

    - `clean_research_project()` rejects a missing value with *"You have to select a research
      project."* — a `200` (re-rendered form) that's easy to mistake for success if you only
      check the status code.
    - `timezone` is worse: nothing rejects a blank value at import time. The server persists
      locations via `Location.objects.bulk_create()`, which **skips normal model validation** —
      so a blank/omitted timezone silently creates locations with a corrupt `timezone` value.
      Nothing fails until *later*, when something lists or filters those locations (this API,
      or the classic web UI's own location list) and the serializer trips over the bad value —
      typically a `500` on an otherwise-unrelated request, long after the import reported
      success. This method requires `timezone` up front specifically to prevent creating that
      kind of latent, hard-to-diagnose corruption.

### Waiting for the import to land

On Trapper v2 the import runs in the background: `import_locations()` returning `True` means the
table was validated and queued, not that the rows exist yet. Neither version exposes the import
task through the API, so `wait_for_import()` checks the outcome instead — it polls until every
`locationID` is listed:

```python
client.locations.import_locations(file="locations.csv", research_project=1, timezone="Europe/Madrid")
client.locations.wait_for_import(["don-01", "don-02"], timeout=60)   # raises TimeoutError if missing
```

Pass `raise_on_timeout=False` to get `False` back instead. It works the same on v1.

There's also a ready-to-run script: [`examples/import_locations.py`](https://github.com/wildintelproject/wildintelproject-trapper-sdk/blob/refactor/examples/import_locations.py).

### What you get in the exception when the CSV itself is rejected

If the CSV fails the server's table validation (wrong/missing columns, a `locationID` that already
exists in this research project, ...), the raised `err.APIError` includes the actual per-row
messages, not just the generic banner — e.g.:

```
Location import failed (status 200): locationID 'dona-001' already exists; longitude must be a number
```

The server renders those details as a JSON blob for a JS widget, not as plain HTML text — see
[`APIClientBase._extract_html_error_text`](../api/api_client_base.md) for how this is parsed out.

### Uploading a very large CSV: `split`

There's no chunked/resumable upload protocol on this endpoint — unlike the `HTTPUploader` component
(a separate, true chunked uploader for a different endpoint), it's a plain single-request form POST.
If a large CSV gets rejected or times out, pass `split=True` to break it into several smaller,
self-contained CSV chunks (each repeating the header row) and import them one request at a time:

```python
client.locations.import_locations(
    file="huge_locations.csv",
    research_project=7,
    timezone="Europe/Madrid",
    split=True,
    delay=2,        # seconds between chunk uploads — defaults to 1
    chunk_size=512 * 1024,  # bytes per chunk — this is also the default
)
```

`split` is not compatible with `gpx_file` (raises `ValueError`) — splitting only makes sense for
the CSV path, and the server rejects a request carrying both file types anyway. With
`raise_on_error=True` (the default), the whole call raises as soon as one chunk fails, without
uploading the rest; with `raise_on_error=False` it uploads every chunk regardless and returns
`False` if any of them failed.

### Retrying a chunk that times out: `retry_attempts`

If a chunk is still too large/slow for the server, the request itself can fail with a network-level
timeout (rather than a normal error response) before the server even gets to respond. That's
retried automatically — using [tenacity](https://github.com/jd/tenacity), with exponential
backoff — up to `retry_attempts` times:

```python
client.locations.import_locations(
    file="huge_locations.csv",
    research_project=7,
    timezone="Europe/Madrid",
    split=True,
    chunk_size=128 * 1024,  # try smaller chunks if the server keeps timing out
    retry_attempts=5,       # default is 3
    retry_min_wait=2,       # seconds, default 1
    retry_max_wait=30,      # seconds, default 10
)
```

Only network-level failures (timeouts, connection resets, ...) are retried — never an HTTP error
response (a 4xx/5xx from the server is a validation failure, not something a retry fixes). Set
`retry_attempts=1` to disable retrying.

## Related: locations as GeoJSON

For map rendering, use [`client.locations_geojson`](locations_geojson.md) instead — a different
endpoint returning a single GeoJSON `FeatureCollection`, with its own filter set (bounding box,
radius, ...).
