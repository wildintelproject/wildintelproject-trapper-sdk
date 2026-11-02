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

## What differs

| Feature | v1 | v2 |
|---|---|---|
| Package upload | `HTTPUploader` (custom chunked protocol) | `TusUploader` (tus 1.0 / tusd) |
| `client.upload_auth()` | — | ✔ |
| `client.maps`, `client.locations_geojson` | ✔ | `UnsupportedVersionError` |
| `collections.*_ondemand` | ✔ | `UnsupportedVersionError` |
| `locations.import_locations`, `deployments.import_deployments` | ✔ | `UnsupportedVersionError` (v2 imports through the Django admin) |
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
