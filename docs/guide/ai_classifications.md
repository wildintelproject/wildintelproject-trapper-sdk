# AI Classifications

!!! info "Trapper compatibility"
    **v1** ✔ · **v2** ✔ — checked against both. See [Trapper versions](versions.md).

`client.ai_classifications` — classification observations produced by an AI provider.

**Endpoints:**

- `GET /media_classification/api/ai-classifications` (list + detail)
- `GET /media_classification/api/ai-classifications/results/{project_pk}/` — CSV/model export for one project

## Filters

The same filters for the list and the AI results table (`export()`). Trapper ignores a filter it does not apply,
without an error, and returns every row: the SDK emits an `UnknownFilterWarning`.

| Parameter | Type | Version | Description |
|---|---|---|---|
| `project` | PK | both | Classification project. **Needed for `deployment` and `collection`** in the list (`ValueError` without it) |
| `deployment` | list of PKs | both | Deployment PKs of the project |
| `collection` | list of PKs | both | PK of the **link** between the project and the collection |
| `ai_provider` | list of PKs | both | AI provider (model) PKs |
| `confidence` | number 0-1 | both | Some observation has at least this confidence |
| `approved` | boolean | both | It became the final classification. **v2: the table answers 500** (the SDK warns) |
| `bboxes` | boolean | both | Has bounding boxes |
| `ftype` | choice | both | Resource type (`I`, `V`, ...) |
| `species` | list of PKs | both | Species PKs |
| `observation_type` | choice | both | Observation type |
| `search` | text | both | Species (Latin or English name), resource name or attribute (list) |
| `owner`, `user`, `feedback` | | v2 | As in the [user list](user_classifications.md) |
| `locations_map`, `rdate_from`/`rdate_to`, `rtime_from`/`rtime_to` | | v2 | Location, date and time of the resource |
| `sex`, `age`, `classified`, `classified_ai` | | v2 | As in the user list |

v1 also applies one filter per custom attribute of the project's classificator, when `project` is given.

## The six access patterns

```python
page = client.ai_classifications.get(page=1, page_size=50, ai_provider=1)
for row in client.ai_classifications.where(species=42):
    print(row)
result = client.ai_classifications.get_all(page_size=100)
row = client.ai_classifications.find(1)
```

See [Usage](../usage.md) if any of this looks unfamiliar — it's the same interface on every component.

## What a row has on each version

The list reads the same on both versions, but v2 sends less: no `owner`, `owner_profile`, `classification` or
`created_at` (they are `None`), and `updated_at` may be `None`. v2 adds `is_setup`, `bboxes` and
`classification_project`.

Each observation of `dynamic_attrs` has `observation_type`, `species`, `count` and `classification_confidence`
as text, as v1 sends them. The confidence is a fraction (`"0.93"`) on both versions — v2 sends it as a percentage
next to the value, and the SDK converts it —, the same scale as the `confidence` filter (`confidence=0.9`).
A missing species, which Trapper writes as the text `"None"`, is `None`.

## Export, scoped to a project

Unlike every other component, `export()` here has a **different signature**: it requires a
`classification_project_pk` (the underlying endpoint needs one, and there's no unscoped export):

```python
client.ai_classifications.export(
    classification_project_pk=7,
    file="ai_results.csv",
)

# Or get model instances instead of a file
records = client.ai_classifications.export(classification_project_pk=7, file=None)
```

It is a table with one row per observation, with the same columns as the
[results table](classifications.md) of `client.classification_results`, and is read the same way:
`AIClassificationRecordExportCamTrap` rows by default and `AIClassificationRecordExportTrapper` rows (with `_id`
and the boxes in `bboxes`) with `camtrapdp=False`. A project with no AI classifications, or none that match the
filters, gives no rows (`[]`, or an empty file) instead of Trapper's `400 "Empty queryset"`.

`raw=True` (or `validate=False`, as before) saves the CSV as Trapper sends it.

Additional field on the export endpoint:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `camtrapdp` | boolean | `True` | `True` = CamtrapDP standard rows, `False` = Trapper's internal format |
