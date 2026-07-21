# Classification Media

`client.classification_media` — media rows (with download URLs) for a classification project.

**Endpoint:** `GET /media_classification/api/media/{project_pk}/`.

!!! note "Not directly usable via `get()`/`where()`"
    The endpoint needs a `project_pk` in its URL, so calling the generic `get()`/`get_all()`/`where()`/
    `all()`/`find()` inherited from every component wouldn't work here — use the `_project_media`/
    `_collection_media` methods below instead, all of which resolve the URL for you.

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
| `classified` | boolean | Classified by user |
| `classified_ai` | boolean | Classified by AI |
| `approved` | boolean | Classification approved |
| `bboxes` | boolean | Has bounding boxes |
| `species` | list of PKs | Filter by species PKs |
| `observation_type` | choice | Filter by observation type |
| `sex` | choice | Filter by sex |
| `age` | choice | Filter by age |

**Extra params** (independent of filtering):

| Parameter | Type | Default | Description |
|---|---|---|---|
| `trapper_url` | bool | `True` | Include absolute Trapper URLs for each media |
| `trapper_url_token` | bool | `True` | Include access tokens in URLs |
| `private_human` | bool | `True` | Include human preview URL |
| `private_vehicle` | bool | `True` | Include vehicle preview URL |
| `private_species` | list | `[]` | List of species to hide |

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
