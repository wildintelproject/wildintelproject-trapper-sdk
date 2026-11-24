# Classifications

!!! info "Trapper compatibility"
    **v1** ✔ · **v2** ✔ — except `import_classifications(overwrite_attrs=True)`, which is **v1 only**. See [Trapper versions](versions.md).

`client.classification_results` — the **final classifications** of a classification project.

## What it represents

In a classification project every resource has one **final classification**: the record that holds the result for
that resource (what it shows), taken from the classification someone made or imported and then approved (from
Trapper's source). `approved` says whether that has happened; the resources nobody has classified have a final
classification too, with the observation type `unclassified`. This component reads those records in three ways, each
with its own shape (checked on Trapper v1 and v2):

| | List (`where()`, `find()`) | Results table (`where_project_results()`, `export_project_results()`) | Import |
|---|---|---|---|
| One row per | **resource** | **observation** (a resource with two species has two rows) | the `_id` of a final classification |
| Species | text (`"European Rabbit (Oryctolagus cuniculus)"`), no pk | `scientificName` | `scientificName` |
| `sex`, `lifeStage`, `behavior`, `bboxes` | **not there** | yes | yes |
| Identifier | `pk`, the primary key of the classification | `_id` (only with `camtrapdp=False`); `observationID` is only the **row number** in the table you asked for (it changes with the filters) and is not in the list | `_id` |
| Needs a project | for `deployment` and `collection` | yes, in the URL | yes |

So **to know what each image shows, use the results table**; the list tells you which resources are classified and
approved, and nothing more. Its `dynamic_attrs` carry only `observation_type`, `species` and `count`.

### What each thing is

- **Classification:** what one person (or the AI) decided about one resource. Each user's classification of a resource
  is its own record (`user_classifications`, see [User classifications](user_classifications.md)); the **final**
  classification is the one record per resource that this component reads. When someone's classification is approved,
  the final one points to it and takes its values (from Trapper's source): it is **one** classification chosen, not a
  merge of several.
- **Observation:** one thing seen in the resource, with its type (`animal`, `human`, `blank`, ...), species, `count`,
  `sex`, `lifeStage` and `behavior`. It is a row of the results table. Two species in one image are two observations;
  an image with nothing in it is one (`blank` or `unclassified`).
- **Bounding box:** an optional position of the observation in the image (`bboxX`, `bboxY`, `bboxWidth`, `bboxHeight`,
  and the `bboxes` list with `camtrapdp=False`). It says *where*, not *what*: what is there is said by the observation,
  and who said it by `classificationMethod` (`human` or `machine`) and `classifiedBy`. An observation can have several
  boxes (a count of three) or none.
- **`_id`:** the primary key of the final classification of the resource, the same as the `pk` of the list. It is the
  stable identifier, and the one the import needs.
- **`observationID`:** only the **number of the row** in the table you asked for. It changes with the filters (the
  same observation is 4 in the whole table and 1 with `sex=male`), so it does not identify an observation and cannot
  be compared between two requests.

!!! note "Two people, one image"
    The results table has the **final** classification only, so it never holds two users' observations of the same
    image. To read what each user said, use [`user_classifications`](user_classifications.md). Trapper does not
    link an observation of one classification with one of another (from its source: they are independent records, and
    it has no matching of boxes): to tell whether two observations are the same animal, compare the boxes yourself
    when both have them, and the species and the count when they do not. *Not checked with two users on one image: the
    test servers have one.*

!!! note "Not to be confused with the media table"
    [`client.classification_media`](classification_media.md) is the table of the project's *files*; this is *what
    they show*. Join them by `mediaID`: there is an example there.

!!! note "Reading, then editing"
    The API cannot create, edit or approve a classification: the list is read-only (`Allow: GET, HEAD, OPTIONS`
    on v1 and v2) and the only write is the [import](#importing-observations-from-a-csv). To correct classifications
    by script: export the results table with **`camtrapdp=False`** (the format that carries `_id`, which the import
    requires; the default `camtrapdp=True` does not), edit it and import it.

**Endpoints:**

- `GET /media_classification/api/classifications` (list + detail)
- `GET /media_classification/api/classifications/results/{project_pk}/` — CSV/model export of observations for one project
- `POST /media_classification/api/classifications/import/` — import observations from a CSV

## Filters

| Parameter | Type | Description |
|---|---|---|
| `project` | PK | The project of the list. **Required for `deployment` and `collection`**: Trapper checks them against the project's own and, without it, answers `400 "Select a valid choice"`. The project-scoped methods below take it from the URL |
| `owner` | boolean | `true` = resources where user is owner/manager |
| `deployment` | list of PKs | Deployment PKs (needs `project`) |
| `collection` | list of PKs | The pk of the **link between the project and the collection**, not the collection's pk (needs `project`; see entry 51 of `TRAPPER_API_IMPROVEMENTS.md`) |
| `locations_map` | comma-separated PKs | Filter by location PKs |
| `rdate_from` / `rdate_to` | date | `date_recorded` range |
| `rtime_from` / `rtime_to` | HH:MM | Time-of-day range |
| `ftype` | choice | Resource type (IMAGE, VIDEO, ...) |
| `bboxes` | boolean | Has bounding boxes |
| `classified`, `classified_ai` | boolean | Has a classification by a user / by AI |
| `approved` | boolean | Approved. **v2 only**: v1 ignores it and calls the same filter `status` |
| `status` | boolean | Approved, on **v1 only** (v2 ignores it) |
| `species` | list of PKs | Filter by species PKs |
| `observation_type` | choice | Filter by observation type |
| `sex` | choice | Filter by sex |
| `age` | choice | Filter by age |

!!! warning "Filters that this endpoint ignores"
    Trapper ignores a parameter it does not know **without an error**, and the list comes back unfiltered. Besides
    the ones above, `user`, `feedback`, `confidence` and `ai_provider`, which a previous version of this guide listed,
    do nothing here (checked on v1 and v2: `user=1` and `ai_provider=1` return every row; they belong to the lists of
    user and AI classifications). A filter that leaves no row answers `200` with an empty list, but the results table
    and the media table answer `400 "Empty queryset..."`.

## The six access patterns

```python
page = client.classification_results.get(page=1, page_size=50, approved=True)
for row in client.classification_results.where(species=42):
    print(row)
result = client.classification_results.get_all(page_size=100)
row = client.classification_results.find(1)
```

See [Usage](../usage.md) if any of this looks unfamiliar — it's the same interface on every component.

## Observation export, scoped to a project

The export endpoint returns a *different* schema than the one above — CamtrapDP or Trapper-flavoured
observation rows (`ClassificationRecordExport`), depending on what the server returns:

```python
# One page
page = client.classification_results.get_project_results(
    project_pk=7, page=1, page_size=50, approved=True,
)
for row in page.results:
    print(row.observationID, row.scientificName)

# Lazy iteration
for row in client.classification_results.where_project_results(project_pk=7):
    print(row)

# Straight to CSV
client.classification_results.export_project_results(project_pk=7, file="observations.csv")

# Or get model instances instead of a file
records = client.classification_results.export_project_results(project_pk=7, file=None)
```

Additional field on the export endpoints:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `camtrapdp` | boolean | `True` | `True` = CamtrapDP standard rows, `False` = Trapper's internal format |

## Importing observations from a CSV

Unlike locations/deployments import (which simulate an HTML form), this is a **real, token-authenticated
REST endpoint** — the proper way an import should look, and the model the locations/deployments
workarounds explicitly fall short of.

```python
result = client.classification_results.import_classifications(
    project_id=7,
    file="observations.csv",
    approve=True,
    import_bboxes=True,
    import_expert_classifications=True,
    import_ai_classifications=False,   # set True + ai_provider_id to import AI rows too
    overwrite_attrs=False,
)
print(result.data.message, result.data.task_id)
```

If the server runs the import as a Celery task, `result.data.task_id` is set and the message tells
you it's running asynchronously; otherwise the message reflects the synchronous result.

### Splitting large CSVs

Like `import_locations`/`import_deployments`, this accepts `split`/`delay`/`chunk_size` to break a
large CSV into several smaller, self-contained chunks (each repeating the header row), uploaded one
at a time with a delay between them:

```python
results = client.classification_results.import_classifications(
    project_id=7, file="huge_observations.csv",
    split=True, delay=2,  # <=512 KiB chunks, 2s apart
)
for r in results:
    print(r.data.message, r.data.task_id)
```

With `split=True` the return value is a **list** of results (one per chunk), instead of a single one.

### Retrying timed-out uploads

If a chunk is still too large/slow for the server, the upload can fail with a network-level timeout
rather than a normal error response. `retry_attempts`/`retry_min_wait`/`retry_max_wait` retry that
specific failure mode (using [tenacity](https://github.com/jd/tenacity), exponential backoff) —
never a 4xx/5xx response, since that's a validation failure a retry can't fix:

```python
client.classification_results.import_classifications(
    project_id=7, file="observations.csv",
    split=True, chunk_size=128 * 1024,  # smaller chunks if the server keeps timing out
    retry_attempts=5, retry_min_wait=2, retry_max_wait=30,
)
```

Set `retry_attempts=1` to disable retrying.

!!! note "This endpoint doesn't need it the way locations/deployments do"
    Unlike locations/deployments, this is a real REST endpoint meant to take a full file in one
    request — only reach for `split` if a large CSV hits a request-size limit or times out.

!!! note "This updates existing classifications — it doesn't create new observations"
    The CSV's `_id` column must reference classifications that **already exist** in the target
    project (the server checks it against a whitelist of that project's classification PKs and
    rejects anything else). This import re-applies expert/AI classification data (species, count,
    approval, ...) to those existing rows — it's not a way to add brand-new observations from
    scratch.

There's also a ready-to-run script: [`examples/import_classifications.py`](https://github.com/wildintelproject/wildintelproject-trapper-sdk/blob/refactor/examples/import_classifications.py).
It has a `--fetch N` mode that writes N *real* existing observation rows from your own project to
a CSV (read-only, safe) — since a CSV with made-up `_id` values will always be rejected, this is the
practical way to get something you can actually test with.
