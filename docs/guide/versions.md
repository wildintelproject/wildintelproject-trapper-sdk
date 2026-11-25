# Trapper versions (v1 and v2)

The SDK talks to both Trapper v1 and Trapper v2 (`2.0.0a2` at the time of writing).

```python
client = TrapperClient(access_token="...", base_url="https://trapper.example.org")
client.server_version          # "v1" or "v2" — detected once, then cached
client.server_release          # exact release, e.g. "2.0.0a" (None if the server does not report it)
```

## Version detection

With `trapper_version="auto"` (the default) the client reads the public `GET api/cs/version/`
and takes the major number of the release it reports:

| Release reported | Version |
|---|---|
| `v1.7.4-2-g7540e9ed` | v1 |
| `2.0.0a` | v2 |

The exact string is available as `client.server_release`.

If that endpoint gives no usable answer (an old build, or an invalid token: DRF answers `401` even on
public routes), the client falls back to `GET storage/api/upload-auth/`, a route that exists only in v2:

| Answer | Meaning |
|---|---|
| `404` | v1 |
| `200`, `401`, `403` | v2 (the route exists, whatever the token is worth) |
| anything else | inconclusive → `APIError`; set the version yourself |

Skip the probe by passing `trapper_version="v1"` or `"v2"`.

## The new API of Trapper 2 (`ninja`)

Trapper 2 is getting a new API under `/api/v2/...` (branch `refactor-api-ninja`, release `2.0.0a4`), with a versioned,
documented schema. While it is being built the server serves both, the old routes and the new ones. The SDK uses the
new one when it is there:

```python
client = TrapperClient(access_token="...", base_url="https://trapper.example.org")
client.server_version   # "v2": it is Trapper 2.x
client.api_flavor       # "ninja" when the server serves the new API, otherwise "legacy"
```

With `trapper_version="auto"`, a v2 server that answers `GET api/v2/probe/auth/` (`200` or `401`; v1 and the first v2
answer `404`) uses the new API. `trapper_version="ninja"` forces it, and `trapper_version="v2"` keeps the old routes.

On the new API:

- The lists use its routes: locations, deployments, resources (also by collection and location), collections,
  research projects and their collections, classification projects and their collections, classificators, final,
  user and AI classifications, the classifications map, sequences, species and users. The tables, exports and
  imports still go through the old routes for now.
- Lists are ordered by `pk` (`sort_by=pk`) unless you pass `sort_by`: its pages never repeat or skip rows. `sort_by`,
  `reverse` and `all_filtered` are accepted.
- `deployment` and `collection` of the classification lists work without `project`.
- The collections of a research project the user cannot see answer `403` (the old route answered an empty list).

## What differs

| Feature | v1 | v2 |
|---|---|---|
| Package upload | `HTTPUploader` (custom chunked protocol) | `TusUploader` (tus 1.0 / tusd) |
| `client.upload_auth()` | — | ✔ |
| `client.maps`, `client.locations_geojson` | ✔ | `UnsupportedVersionError` (use `deployments.geojson()`) |
| `deployments.geojson()` | `UnsupportedVersionError` | ✔ (`api/deployments/geojson/`) |
| `collections.*_ondemand` | ✔ | `UnsupportedVersionError` |
| `locations.import_locations`, `deployments.import_deployments` | ✔ (web import form) | ✔ (Django admin import action; needs a staff account, runs asynchronously) |
| `classification_results.import_classifications(overwrite_attrs=True)` | ✔ | `UnsupportedVersionError` (v2 removed the option) |
| `client.project_deployments` | `UnsupportedVersionError` | ✔ |
| `research_projects.create()` | ✔ (web form) | `UnsupportedVersionError` |
| `classification_projects.create()`, `.add_collections()`, `.remove_collection()` | ✔ (web forms) | `UnsupportedVersionError` |
| `classificators.create()` | ✔ (web form) | `UnsupportedVersionError` |
| Everything else | ✔ | ✔ |

## Uploading

```python
uploader = client.get_uploader()          # HTTPUploader on v1, TusUploader on v2
uploader.upload(Path("/data/package.zip"), "season1/package.zip")
```

On v2 the uploader authenticates with `Authorization: Token ...`, so the client needs an
`access_token`. Call `client.upload_auth()` first to find out, before any byte moves, whether the
token may upload (`403` = no uploader account). An interrupted upload resumes from the last byte
the server holds; its URL is kept in a `<file>.tusmeta.json` sidecar.

### Uploader account (v2)

A valid token is not enough to upload on v2: the user also needs an **HTTP uploader account**
(`UserHttpUploaderAccount`), which a Trapper administrator grants in the Django admin
(*Accounts → User HTTP uploader accounts → Add*, pick the user). Without it the server refuses the
upload with `403 "HTTP uploader access not granted"`.

```python
try:
    client.upload_auth()                    # {"username": "..."} when the token may upload
except err.ForbiddenError:
    ...                                     # valid token, but no uploader account yet
except err.UnauthorizedError:
    ...                                     # unknown or missing token
```

Check it once before a long upload instead of finding out at the first byte. v1 has no such
requirement (and no `upload_auth()`: it raises `UnsupportedVersionError`).
