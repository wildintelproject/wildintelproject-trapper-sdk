# Classification Media

!!! info "Trapper compatibility"
    **v1** ✔ · **v2** ✔ — same code on both. See [Trapper versions](versions.md).

`client.classification_media` — media rows (with download URLs) for a classification project.

**Endpoint:** `GET /media_classification/api/media/{project_pk}/`.

!!! note "Not directly usable via `get()`/`where()`"
    The endpoint needs a `project_pk` in its URL, so calling the generic `get()`/`get_all()`/`where()`/
    `all()`/`find()` inherited from every component wouldn't work here — use the `_project_media`/
    `_collection_media` methods below instead, all of which resolve the URL for you.

## What it represents

A **classification project** takes collections of resources and records what is in each one (its
*classification*). `client.classification_media` is the **media table of that project**: one row per resource of
the project, in the shape of the Camtrap DP *media* file (Trapper builds it from the project's final
classification of each resource, from its source). It is **not** a list of every resource in Trapper: a resource
that is in no classification project has no row here, and so no download URL with a token. For those, see
[Downloading the file](resources.md#downloading-the-file) in the resources guide.

Each row is a [`Media`](../api/schemas/classifications.md), the same eleven columns on Trapper v1 and v2:

| Column | What it is |
|---|---|
| `mediaID` | The **primary key of the resource** (`Resource.pk`) |
| `deploymentID` | The deployment's `deployment_id` text (`don01-2024a`), not its primary key |
| `captureMethod` | How the deployment captures (`activityDetection` in Trapper's data) |
| `timestamp` | `date_recorded`, with its UTC offset (`2024-03-19T13:30:31+0100`) |
| `filePath` | The URL to download the file, with the resource's token when the file is public (see below) |
| `filePublic` | `True` when `filePath` carries the token, `False` when it does not |
| `fileName` | The resource's name, **without extension** (`don01-2024a_0004`) |
| `fileMediatype` | Its MIME type (`image/jpeg`) |
| `exifData` | Always empty: Trapper does not fill it (from its source) |
| `favorite`, `mediaComments` | Flag and comments; empty in the data checked |

How it arrives: the server sends the whole table as one gzip CSV and **ignores paging**. `page_size` has no
effect, and `page=2` returns the same rows as `page=1`, with `pages=1`. `where_project_media()` and `get_all`
are fine with that; do not rely on `page` to walk it.

!!! note "What is in each image is not here"
    The table describes the **resources of the classification project** and their files, not what they show. There is
    no animal, vehicle, species, count, sex or bounding box in a row: that is in the project's classification
    results ([`client.classification_results`](classifications.md)). A resource that is in no classification project
    has no row here either. To have both, join them by `mediaID`:

    ```python
    seen = {}
    for obs in client.classification_results.where_project_results(7):
        seen.setdefault(obs.mediaID, []).append(obs.observationType)

    for row in client.classification_media.where_project_media(7):
        print(row.fileName, seen.get(row.mediaID))      # don01-2024a_0004 ['animal']
    ```

    The [filters](#filters) do look at the classification (`species`, `observation_type`, ...), so you can ask for
    the images with a lynx, but the row you get back does not say it is a lynx.

### Public and private files

`filePath` is always there, but only a **public** file has `?rt=<token>` in it, and only that URL can be
downloaded with no session. By default Trapper hides the images of **humans** and **vehicles**: their row has
`filePublic` false and a URL without token, which answers `404`. The extra parameters decide it:

- `private_human` and `private_vehicle` (default **hide**): `True` hides the files whose observation is a
  human, or a vehicle; `False` shows them with their token.
- `private_species`: meant to hide the files of some species (primary keys), but Trapper answers **`500`** with any
  value, an empty one included (checked on v1 and v2). Do not use it.
- `trapper_url_token`: `False` leaves the token out of every URL, so all the rows are private.

!!! note "Booleans: `True`, `False`, or the text"
    Trapper reads only the exact text `True` as true, and any other, `true` included, as false (so a client that sends a
    boolean the usual way gets the opposite). The SDK sends `private_human`, `private_vehicle`, `trapper_url` and
    `trapper_url_token` as `True`/`False` text itself: give a Python boolean, or the text `true`/`false` in any case.
    Anything else (`1`, `"yes"`, `None`) is a `ValueError` before the request. *Before this was done (issue #85),
    `private_human=True` showed the humans.*

For example, with a project that has two images of humans (checked on Trapper v2, 28 rows):

```python
cm = client.classification_media

# The default: humans and vehicles are private. 26 of the 28 rows are public.
rows = list(cm.where_project_media(7))
print(sum(r.filePublic for r in rows))                       # 26
print([r.fileName for r in rows if not r.filePublic])        # the two private ones: their URL has no token

# Treat humans and vehicles as public: every URL carries the token
rows = list(cm.where_project_media(7, private_human=False, private_vehicle=False))
print(sum(r.filePublic for r in rows))                       # 28

# Humans stay private, vehicles do not
rows = list(cm.where_project_media(7, private_human=True, private_vehicle=False))

# The same parameters go to the downloads: with the default, the private files are not downloaded
cm.download_project_media_files(7, "out/", private_human=False, private_vehicle=False)
```

Leave `private_human` as it is if you are going to share the rows or the files: by default the URL of a human
carries no token, so the image cannot be downloaded with it.

A project table with nothing to show (a filter that leaves no rows, or a project the account cannot see) is answered by
Trapper with a `400` ("Empty queryset or you have no permission..."), not an empty list. The SDK reads it as **an empty
result** in `get_*`, `where_*`, `export_*` and the downloads (`count` 0, nothing to iterate, `[]`, an empty file), as
the classification list does. The `400` is also the answer to a missing permission, so a project that the account
cannot see looks empty too; any other `400` (a wrong filter value) is still a `BadRequestError`.

## Filters

| Parameter | Type | Description |
|---|---|---|
| `owner` | boolean | `true` = resources where the user is owner or manager |
| `deployment` | list of PKs | Filter by deployment PKs |
| `collection` | list of PKs | Filter by collection PKs |
| `locations_map` | comma-separated PKs | Filter by location PKs |
| `rdate_from` / `rdate_to` | date | `date_recorded` range |
| `rtime_from` / `rtime_to` | HH:MM | Time-of-day range on `date_recorded` |
| `ftype` | choice | Filter by resource type (IMAGE, VIDEO, ...) |
| `classified` | boolean | Classified by user (**`500` on Trapper v2** for this table) |
| `classified_ai` | boolean | Classified by AI (**`500` on Trapper v2** for this table) |
| `approved` | boolean | Classification approved. Works on both: Trapper v1 calls it `status`, and the SDK sends it as such there |
| `bboxes` | boolean | Has bounding boxes |
| `species` | list of PKs | Filter by species PKs |
| `observation_type` | choice | Filter by observation type |
| `sex` | choice | Filter by sex |
| `age` | choice | Filter by age |

**Extra params** (independent of filtering):

| Parameter | Type | Default | Description |
|---|---|---|---|
| `trapper_url` | bool | `True` | Read by Trapper but not used: the URL is always absolute (from its source) |
| `trapper_url_token` | bool | `True` | `False` leaves the token out of every URL (all the files are then private) |
| `private_human` | bool | `True` | `True` hides the files of humans (see [Public and private files](#public-and-private-files)) |
| `private_vehicle` | bool | `True` | `True` hides the files of vehicles |
| `private_species` | list of PKs | `[]` | Meant to hide the files of those species; answers `500` with any value |

## Media for a whole project

```python
# One page
page = client.classification_media.get_project_media(project_pk=7, page_size=200)

# Lazy iteration
for row in client.classification_media.where_project_media(project_pk=7, deployment=12):
    print(row)

# CSV export
client.classification_media.export_project_media(project_pk=7, file="media.csv")

# Find one media row by its media/resource ID
row = client.classification_media.get_project_media_by_id(project_pk=7, media_id=4831)
```

## Media scoped to a collection within the project

```python
page = client.classification_media.get_collection_media(project_pk=7, collection_pk=5)

for row in client.classification_media.where_collection_media(project_pk=7, collection_pk=5):
    print(row)

client.classification_media.export_collection_media(
    project_pk=7, collection_pk=5, file="collection_media.csv",
)
```

## Downloading the actual files

Each media row's `filePath` is an absolute, ready-to-download URL (it already carries the
resource's access token) — required for private resources, since the underlying file-serving view
isn't part of the DRF API and doesn't honor the `Authorization` header.

```python
# Download every media file from a project
files = client.classification_media.download_project_media_files(
    project_pk=7, output_dir="media",
)

# Same, but scoped to a collection, in parallel, compressed into one ZIP
files = client.classification_media.download_collection_media_files(
    project_pk=7, collection_pk=5, output_dir="collection_media",
    parallel=True, compress=True,
)

# Download one file directly if you already have its URL
path = client.classification_media.download_media_file(
    file_url=row.filePath, file="media_4831.jpg",
)
```

Nothing but the URL is sent: no API token and no session, so it works with a token alone. The file is
streamed to a temporary `.part` file that is moved into place when complete, so a failed download never leaves
a half-written file. Network failures and `502`/`503`/`504` answers are retried with exponential backoff
(`retry_attempts`, `retry_min_wait`, `retry_max_wait`); a `404` (a missing file or a token that is no longer
valid) is a `NotFoundError` and is not retried.
