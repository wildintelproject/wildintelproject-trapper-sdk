# AI Classifications

`client.ai_classifications` — classification observations produced by an AI provider.

**Endpoints:**

- `GET /media_classification/api/ai-classifications` (list + detail)
- `GET /media_classification/api/ai-classifications/results/{project_pk}/` — CSV/model export for one project

## Filters

| Parameter | Type | Description |
|---|---|---|
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
page = client.ai_classifications.get(page=1, page_size=50, ai_provider=1)
for row in client.ai_classifications.where(species=42):
    print(row)
result = client.ai_classifications.get_all(page_size=100)
row = client.ai_classifications.find(1)
```

See [Usage](../usage.md) if any of this looks unfamiliar — it's the same interface on every component.

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

Rows are parsed as either the CamtrapDP-flavoured or Trapper-flavoured export schema, depending on
whether the server includes a Trapper-internal `_id` field.

Additional field on the export endpoint:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `camtrapdp` | boolean | `True` | `True` = CamtrapDP standard rows, `False` = Trapper's internal format |
