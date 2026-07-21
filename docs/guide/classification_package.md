# Classification Package

`client.classification_package` — generates (or reuses a cached) Camtrap DP data package for a
classification project, and returns its download URL.

**Endpoint:** `GET /media_classification/api/package/{project_pk}/`.

!!! note "Not directly usable via `get()`/`where()`"
    This is a single fixed-shape JSON response, not a paginated list — use `get_project_package()`
    below.

## Generating and downloading a package

```python
response = client.classification_package.get_project_package(project_pk=7)

print(response.data.message)
print(response.data.package)  # absolute download URL, already carries its own one-time token

file_response = client.make_request(endpoint=response.data.package, method="GET")
with open("camtrapdp_project_7.zip", "wb") as f:
    f.write(file_response.content)
```

`response.data.package`'s URL already carries a one-time access token (`?rt=...`) — download it
as-is via `client.make_request()`, never re-request it through a component method.

There's also a ready-to-run script:
[`examples/download_camtrapdp_for_classification_project.py`](https://github.com/wildintelproject/wildintel-trapper-sdk/blob/refactor/examples/download_camtrapdp_for_classification_project.py).

## Generation/cache parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `clear_cache` | bool | `False` | Force regeneration instead of reusing the cached package |
| `release` | bool | `False` | Mark the generated package as a release |
| `get_released` | bool | `False` | Return the latest already-published release instead |
| `export_format` | str | `"camtrapdp"` | Also accepts `"trapper"` (disables `include_events`) |
| `export_filetype` | str | `"csv.gz"` | File format for the data tables inside the package |

## Content-filtering parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `approved_only` | bool | `True` | Only include approved classifications |
| `exclude_blank` | bool | `False` | Exclude blank observations |
| `all_deployments` | bool | `True` | Include all deployments of the project |
| `filter_deployments` | str | `None` | Comma-separated deployment PKs (when `all_deployments=False`) |
| `include_events` | bool | `False` | Include the events/sequences table |
| `events_count_var` | str | `"count"` | Name of the count variable in the events table |

## Media URL/privacy parameters

Same flags as [Classification Media](classification_media.md):

| Parameter | Type | Default |
|---|---|---|
| `trapper_url_token` | bool | `True` |
| `private_human` | bool | `True` |
| `private_vehicle` | bool | `True` |
| `private_species` | list | `[]` |

## Package metadata parameters

Written into the package's `datapackage.json`:

| Parameter | Type | Default |
|---|---|---|
| `name` | str | `None` |
| `version` | str | `"1.0"` |
| `title` | str | `None` |
| `description` | str | `None` |
| `keywords` | list | `[]` |
| `licenses` | list | `[]` |

```python
response = client.classification_package.get_project_package(
    project_pk=7,
    clear_cache=True,
    approved_only=False,
    title="Doñana camera traps 2026",
    keywords=["camera-trap", "doñana"],
)
```
