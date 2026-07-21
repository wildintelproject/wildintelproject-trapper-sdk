# Classifications

`client.classification_results` — final (approved) classification observations.

**Endpoints:**

- `GET /media_classification/api/classifications` (list + detail)
- `GET /media_classification/api/classifications/results/{project_pk}/` — CSV/model export of observations for one project
- `POST /media_classification/api/classifications/import/` — import observations from a CSV

## Filters

| Parameter | Type | Description |
|---|---|---|
| `project` | PK | Auto-filtered by URL when using the project-scoped export methods below — not needed there |
| `owner` | boolean | `true` = resources where user is owner/manager |
| `deployment` | list of PKs | Filter by deployment PKs |
| `collection` | list of PKs | Filter by collection PKs |
| `locations_map` | comma-separated PKs | Filter by location PKs |
| `rdate_from` / `rdate_to` | date | `date_recorded` range |
| `rtime_from` / `rtime_to` | HH:MM | Time-of-day range |
| `ftype` | choice | Resource type (IMAGE, VIDEO, ...) |
| `bboxes` | boolean | Has bounding boxes |
| `user` | list of PKs | Filter by owner user PKs |
| `approved` | boolean | Has a FINAL approved classification |
| `feedback` | boolean | Is a feedback classification |
| `species` | list of PKs | Filter by species PKs |
| `observation_type` | choice | Filter by observation type |
| `sex` | choice | Filter by sex |
| `age` | choice | Filter by age |
| `confidence` | number | `dynamic_attrs.classification_confidence >= value` |
| `ai_provider` | list of PKs | Filter by AI provider PKs |

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
