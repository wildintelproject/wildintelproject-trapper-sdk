# Classification Package

!!! info "Trapper compatibility"
    **v1** ✔ · **v2** ✔ — checked against both. See [Trapper versions](versions.md).

`client.classification_package` — the **Camtrap DP data package** of a classification project: a zip with
`datapackage.json` and the `deployments`, `media` and `observations` tables (plus `events` with
`include_events=True`).

**Endpoint:** `GET /media_classification/api/package/{project_pk}/`. Trapper builds the package in the request
(seconds for a small project), or takes it from its cache (one per set of parameters; `clear_cache=True` rebuilds
it), and answers `{"data": {"message", "errors", "package"}}`. `package` is the download URL: it carries its own
token (`?rt=...`), works without the API token and stays valid until the package is rebuilt.

## Building and downloading a package

```python
# In one call
path = client.classification_package.download_project_package(7, "doñana.zip", clear_cache=True)

# Or in two
response = client.classification_package.get_project_package(project_pk=7, approved_only=False)
print(response.data.message)
path = client.classification_package.download_package(response, "packages/")   # packages/<id>.zip
```

`download_package()` takes the response or its URL, streams the zip to `<file>.part` and moves it into place, and
retries network failures. There's also a ready-to-run script:
[`examples/download_camtrapdp_for_classification_project.py`](https://github.com/wildintelproject/wildintelproject-trapper-sdk/blob/development/examples/download_camtrapdp_for_classification_project.py).

## Parameters

Trapper ignores any other parameter without an error; the SDK emits an `UnknownFilterWarning`.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `clear_cache` | bool | `False` | Rebuild instead of reusing the cached package |
| `release` | bool | `False` | Mark the package as a release |
| `get_released` | bool | `False` | Return the latest release instead |
| `export_format` | str | `"camtrapdp"` | Or `"trapper"` (Trapper's columns; no events) |
| `export_filetype` | str | `"csv.gz"` | Or `"parquet"` (anything else is a `400`) |
| `split_custom_attrs` | bool | `False` | **v2**, `"trapper"` format: one column per custom attribute (not importable) |
| `approved_only` | bool | `True` | Only approved classifications |
| `exclude_blank` | bool | `False` | Leave out blank observations |
| `all_deployments` | bool | `True` | Every deployment of the project |
| `filter_deployments` | str | | Only deployments whose `deploymentID` **contains** this text (not PKs) |
| `include_events` | bool | `False` | Add the events (sequences) table |
| `events_count_var` | str | `"count"` | Count variable of the events table |
| `trapper_url_token`, `private_human`, `private_vehicle` | bool | `True` | As in [classification media](classification_media.md) |
| `name`, `version`, `title`, `description` | str | | Package metadata (`version` is `"1.0"`) |

!!! warning "`keywords`, `licenses` and `private_species` cannot be sent"
    Trapper types them as lists but reads one text per parameter, and always fails on them (`400`). The SDK
    raises a `ValueError` instead. The package takes the research project's keywords and `private` licenses.

!!! warning "`release` and `get_released`"
    They do not work together through the API: a release built here is stored as a cached package, which
    `get_released` does not look at; and `get_released=True` with no release builds a new package next to the
    cached one, after which Trapper answers `400 "get() returned more than one UserDataPackage"` for those parameters
    (`clear_cache` included) until an admin deletes one (Django admin, *User data packages*). The SDK's error says so.

!!! note "v1: the project needs an admin"
    On v1 the contributors of the package are the admins of the classification project: a project with no admin
    role fails with `[] should be non-empty at property 'contributors'` (the SDK's error says so).

```python
response = client.classification_package.get_project_package(
    project_pk=7,
    clear_cache=True,
    approved_only=False,
    filter_deployments="don",          # deploymentIDs that contain "don"
    title="Doñana camera traps 2026",
)
```
