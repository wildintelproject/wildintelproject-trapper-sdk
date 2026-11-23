# Collections

!!! info "Trapper compatibility"
    **v1** ✔ · **v2** ✔ — except the `*_ondemand` methods, which are **v1 only** (`UnsupportedVersionError` on v2). See [Trapper versions](versions.md).

`client.collections` — storage collections: groups of resources uploaded together.

**Endpoints:**

- `GET /storage/api/collections` (list + detail)
- `GET /storage/api/collections_ondemand` — on-demand collections for the current user
- `GET /storage/api/collections_map` — collections list for map rendering
- `GET /storage/api/collections_append` — collections the user can append resources to
- `POST /storage/api/collection/process/` — trigger processing of an FTP-uploaded collection

## Filters

| Parameter | Type | Description |
|---|---|---|
| `pk` | list of PKs | Filter by specific collection PKs |
| `status` | choice | `Private`, `OnDemand`, `Public` or `Archived` ([`CollectionStatus`](#filtering-by-status)), in any case |
| `owner` | boolean | `true` = only collections owned/managed by current user |
| `owners` | list of PKs | Filter by one or more owner user PKs |
| `research_projects` | list of PKs | Filter by one or more research project PKs |
| `locations_map` | list of PKs | Filter via `resources__deployment__location` (**v1 only**: Trapper v2 ignores it) |
| `search` | string | Full-text search across `name` and owner username |

Lists (`pk`, `owners`, `research_projects`, `locations_map`) can be given as a list or as a comma-separated string:
`pk=[2, 1]` and `pk="2,1"` are the same. Trapper reads `pk` and `locations_map` as one string with commas and
`owners` and `research_projects` as repeated parameters, and `pk=[2, 1]` sent the other way keeps **one** pk; the SDK
sends each one the way Trapper reads it.

### Filtering by status

Trapper compares `status` as it is stored, in upper and lower case, and a value that does not exist is an **empty
result, not an error**: `status="private"` and `status="Bogus"` both give no collections. The SDK resolves it with
`CollectionStatus` (`Private`, `OnDemand`, `Public`, `Archived`), accepting any case, the label (`"On demand"`) or the
member, and raises a `ValueError` listing the valid ones before any request when it is none of them:

```python
from trapper_client import CollectionStatus

client.collections.where(status="public")                    # the same as "Public"
client.collections.where(status=CollectionStatus.ON_DEMAND)
client.collections.where(status="Bogus")                     # ValueError: use one of Private, OnDemand, Public, Archived
```

!!! warning "A filter that Trapper does not apply"
    Trapper ignores a parameter that is not one of its filters **without an error**, and the list comes back
    unfiltered; the SDK emits an `UnknownFilterWarning` that names it (the request is still sent). Besides those in
    the table, the list applies `name`, `period_begin`, `period_end`, `is_complete_cs_collection`, `cs_deployment`,
    `managers` and `members`. `locations_map` is ignored by v2, and `description`, `date_created` and `ordering` by
    both. To silence it: `warnings.simplefilter("ignore", err.UnknownFilterWarning)`.

## The six access patterns

```python
# Lazy iteration (all() is the same thing)
for col in client.collections.where():
    print(col)
for col in client.collections.where(owner=True):
    print(col)
for col in client.collections.where(research_projects=3):
    print(col)

# One page
page = client.collections.get(page=1, page_size=25)
print(page.pagination.count)

# Single item
col = client.collections.find(42)
```

See [Usage](../usage.md) if any of this looks unfamiliar — it's the same interface on every component.

!!! note "Resources inside a collection"
    `CollectionsComponent` only lists *collections themselves* — for the resources inside one, use
    [`client.resources.where_by_collection(collection_pk=...)`](resources.md#scoped-to-a-collection-or-a-location).

## On-demand / map / append sub-endpoints

Three related endpoints get the exact same `where_*`/`get_*`/`get_all_*`/`find_*` set as the main
one, just scoped to a different collection subset:

```python
# On-demand collections for the current user
for col in client.collections.where_ondemand():
    print(col)
page = client.collections.get_ondemand(page_size=25)
result = client.collections.get_all_ondemand()
col = client.collections.find_ondemand(42)

# Collections for map rendering
for col in client.collections.where_map():
    print(col)

# Collections the user can append resources to
for col in client.collections.where_append():
    print(col)
```

What each one gives (checked on Trapper v1 and v2):

| Method | Fields | Pagination | v2 |
|---|---|---|---|
| main (`where()`, `get()`, ...) | the nine of `Collection` | paginated | yes |
| `*_ondemand` | the same nine | paginated | **no**: `UnsupportedVersionError` (Trapper answers `404`) |
| `*_map` | the same nine | **none**: Trapper returns one plain list and ignores `page_size` | yes |
| `*_append` | only `pk` and `name` (the other fields are `None`) | **none**: one plain list | yes |

The SDK wraps a plain list as a single page, so `get_map()` and `get_all_append()` work like the others and
`pagination.count` is the length of the list. `delete_data`, `update_data`, `detail_data` and `owner_profile` are web
page URLs on v1 and `None` on v2.

## Creating a collection from a package

A collection with its resources is created from a **package**: a ZIP with the files and a YAML that describes
them. The SDK has the two steps, and nothing else creates a collection with data: `get_uploader()` puts the two
files in the account's `collections/` folder on the server, and `trigger_collection()` makes Trapper process them.

```python
from pathlib import Path

uploader = client.get_uploader()                       # chunked on v1, resumable (tus) on v2
uploader.upload(Path("package.yaml"), "collections/package.yaml")
uploader.upload(Path("package.zip"), "collections/package.zip")

response = client.collections.trigger_collection({"yaml_file": "package.yaml", "zip_file": "package.zip"})
print(response.json()["data"]["task_id"])              # the task has started: the collection is not there yet

# wait for it: the collection and its resources appear a few seconds later
import time
while not (found := list(client.collections.where(search="My collection"))):
    time.sleep(3)
```

The YAML (Trapper validates it against `collection_schema.yaml`; a problem is a `BadRequestError` with the details in
`data.errors`):

```yaml
collections:
  - name: My collection              # reused if the account already has one with this name (in Trapper's code)
    resources_dir: res               # the folder of the ZIP that holds one folder per deployment
    project_id: 3                    # a CLASSIFICATION project (the research project comes from it)
    timezone: Europe/Madrid          # must be the one of the deployments' locations
    timezone_ignore_dst: false       # and so must this
    managers:                        # optional
      - username: ana
    deployments:
      - deployment_id: don01-2024a   # an existing deployment of the project's research project
        resources:
          - name: don01-2024a_0001
            file: IMG_0001.JPG       # res/don01-2024a/IMG_0001.JPG in the ZIP
            date_recorded: '2024-03-01T10:00:00+01:00'
            mime_type: image/jpeg    # optional, like file_width, file_height, file_size, file_fps, file_duration
```

and the ZIP has `res/don01-2024a/IMG_0001.JPG`, that is `<resources_dir>/<deployment_id>/<file>`.

What it needs (checked on Trapper v1 and v2, except what says *in Trapper's code*):

- The **classification project** and the **deployments** must exist and the account must be able to upload to the
  project. The SDK creates deployments by [import](deployments.md#importing-deployments-write-access), and
  classification projects on v1 only (`client.classification_projects.create()`).
- The `timezone` and `timezone_ignore_dst` of the YAML must match the deployments' locations, or Trapper refuses it.
- The account needs **uploader access** (on v2 an *HTTP uploader account*, see [versions](versions.md)), and on **v1
  the uploader is served by Trapper's nginx**: a development server on its own port answers `404` to the login.
- *In Trapper's code:* a file that is identical (same content) to one already in the deployment, or that has an
  extension Trapper does not accept, is **skipped** and written to a `.log` file next to the ZIP, without failing the rest.
- On **v2 the uploaded files can take a moment to be in place**: if `trigger_collection()` answers `NotFoundError`
  ("not found in your upload directory") right after the upload, wait a couple of seconds and call it again.
- `trigger_ai_pipeline` is `True` by default, and starts the AI detection on the new resources; pass `False` to skip it.
- *In Trapper's code:* the thumbnails and previews are built after the resources exist, so
  `resources.download(pk, ..., kind="thumbnail")` may answer `NotFoundError` for a moment. Once built, they download
  (checked on v1).

## Downloading the files of a collection

`client.collections.download_resources(pk, "downloads/")` saves the files of a collection into
`downloads/<collection name>/`, with the filters of the resource list to choose which ones, skipping what is already
there. See [Downloading all the files of a deployment or a collection](resources.md#downloading-all-the-files-of-a-deployment-or-a-collection).

## Triggering FTP-uploaded collection processing

`trigger_collection()` starts the processing of a data package (a YAML definition and a ZIP) that is **already in
the account's own folder on the server**: it does not upload anything (see the uploader for that).

```python
response = client.collections.trigger_collection(
    payload={
        "yaml_file": "package_123.yaml",
        "zip_file": "package_123.zip",
        "remove_zip": False,
    },
)
print(response.json()["data"]["task_id"])
```

`yaml_file` and `zip_file` are required; `remove_zip` (default `False`), `extract_metadata` (default `False`) and
`trigger_ai_pipeline` (default `True`) are optional. Trapper checks the YAML definition and starts a background
task (it runs in the request itself only if the server has Celery off), so a `200` means it was **started**, not that
the collection exists. The answer is
`{"data": {"message": ..., "errors": ..., "task_id": ...}}`. A missing name or an invalid YAML is a `BadRequestError`
(the problems are in `data.errors`), and a file that is not in the account's folder is a `NotFoundError`; with
`raise_on_error=False` the raw response is returned instead.
