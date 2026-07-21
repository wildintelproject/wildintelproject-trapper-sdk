# Locations

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

## Importing locations (write access)

`/geomap/api/locations` is read-only, so `import_locations()` works around that by simulating the
classic web UI's `geomap/location/import/` form via cookie/session auth instead of the API's token
auth (see [`APIClientBase.session_login`](../api/api_client_base.md)).

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

There's also a ready-to-run script: [`examples/import_locations.py`](https://github.com/wildintelproject/wildintel-trapper-sdk/blob/refactor/examples/import_locations.py).

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
