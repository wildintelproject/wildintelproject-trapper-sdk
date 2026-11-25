# Classifications Map

!!! info "Trapper compatibility"
    **v1** ✔ · **v2** ✔ — checked against both. See [Trapper versions](versions.md).

`client.classifications_map` — the final classifications in a light form, as the map of the classification UI uses
them.

**Endpoint:** `GET /media_classification/api/classifications_map` (list + detail). The same rows and filters as the
list of [classification results](classifications.md) (every final classification the user can see), but:

- **Not paginated**: one answer with every row; `page` and `page_size` do nothing.
- **Less in each row** (`ClassificationMap`): the resource (its `deployment` is the `deploymentID`), the project,
  and `dynamic_attrs` with **only the custom attributes** of the classificator — no observation type, species or
  count. Use `client.classification_results` for them.

## Filters

Those of the classification list. Trapper ignores any other without an error; the SDK emits an
`UnknownFilterWarning`.

| Parameter | Type | Description |
|---|---|---|
| `project` | PK | The project. **Needed for `deployment` and `collection`** (`ValueError` without it) |
| `owner` | boolean | `true` = resources where the user is owner/manager |
| `deployment` | list of PKs | Deployment PKs of the project |
| `collection` | list of PKs | PK of the **link** between the project and the collection |
| `locations_map` | comma-separated PKs | Location PKs |
| `rdate_from` / `rdate_to` | date | `date_recorded` range |
| `rtime_from` / `rtime_to` | HH:MM | Time-of-day range |
| `ftype` | choice | Resource type (`I`, `V`, ...) |
| `classified` / `classified_ai` | boolean | Has a classification by a user / by AI |
| `approved` | boolean | Approved. Works on both versions: v1 calls it `status` and the SDK sends it as such |
| `bboxes` | boolean | Has bounding boxes |
| `species` | list of PKs | Species PKs |
| `observation_type`, `sex`, `age` | choice | Observation type, sex, age |

## Usage

```python
rows = client.classifications_map.get_all(project=7, approved=True).results
for row in client.classifications_map.where(project=7, deployment=[3, 4]):
    print(row.resource.name, row.resource.deployment, row.dynamic_attrs)
row = client.classifications_map.find(231)
```
