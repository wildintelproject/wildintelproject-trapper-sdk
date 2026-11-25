# User Classifications

!!! info "Trapper compatibility"
    **v1** ✔ · **v2** ✔ — checked against both. See [Trapper versions](versions.md).

`client.user_classifications` — individual (non-final) classifications made by human users, before
they're approved into a [final classification](classifications.md).

**Endpoint:** `GET /media_classification/api/user-classifications` (list + detail).

## Filters

Trapper ignores a filter it does not apply, without an error, and returns every row: the SDK emits an
`UnknownFilterWarning` for a name the server's version does not apply.

| Parameter | Type | Version | Description |
|---|---|---|---|
| `project` | PK | both | Classification project. **Needed for `deployment` and `collection`** (`ValueError` without it) |
| `deployment` | list of PKs | both | Deployment PKs of the project |
| `collection` | list of PKs | both | PK of the **link** between the project and the collection |
| `user` | list of PKs | both | Who classified (user PKs) |
| `owner` | boolean | both | `true` = the user's own classifications |
| `approved` | boolean | both | It became the final classification |
| `feedback` | boolean | both | It is a feedback classification |
| `bboxes` | boolean | both | Has bounding boxes |
| `ftype` | choice | both | Resource type (`I`, `V`, ...) |
| `species` | list of PKs | both | Species PKs |
| `observation_type` | choice | both | Observation type |
| `locations_map` | comma-separated PKs | both | Location PKs |
| `rdate_from` / `rdate_to` | date | both | `date_recorded` range |
| `rtime_from` / `rtime_to` | HH:MM | both | Time-of-day range |
| `search` | text | both | Species (Latin or English name), resource name or attribute |
| `sex`, `age` | choice | v2 | Sex, age |
| `classified` / `classified_ai` | boolean | v2 | The resource has a user / AI classification |

v2 also applies the fields of its model (`is_blank`, `has_animals`, `classification_type`, ...) and one filter per
custom attribute of the project's classificator.

## What a row has

The resource, the observations (`dynamic_attrs`: `observation_type`, `species` and `count`, as text; a missing
species is `None`) and whether it became the final classification (`approved`). v2 does not send `classification`
or `created_at`, and adds `is_feedback`, `is_setup`, `bboxes` and `classification_project`.

## The six access patterns

This component has no special methods — it's exactly the generic interface described in
[Usage](../usage.md):

```python
page = client.user_classifications.get(page=1, page_size=50, approved=True)
for row in client.user_classifications.where(species=42):
    print(row)
result = client.user_classifications.get_all(page_size=100)
row = client.user_classifications.find(1)
client.user_classifications.export(file="user_classifications.csv")
```
