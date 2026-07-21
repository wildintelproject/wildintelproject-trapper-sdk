# User Classifications

`client.user_classifications` — individual (non-final) classifications made by human users, before
they're approved into a [final classification](classifications.md).

**Endpoint:** `GET /media_classification/api/user-classifications` (list + detail).

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
| `classified` | boolean | Classified by humans |
| `classified_ai` | boolean | Classified by AI |
| `bboxes` | boolean | Has bounding boxes |
| `approved` | boolean | Has a FINAL approved classification |
| `feedback` | boolean | Is a feedback classification |
| `species` | list of PKs | Filter by species PKs |
| `observation_type` | choice | Filter by observation type |
| `sex` | choice | Filter by sex |
| `age` | choice | Filter by age |

## The six access patterns

This component has no special methods — it's exactly the generic interface described in
[Usage](../usage.md):

```python
page = client.user_classifications.get(page=1, page_size=50, classified=True)
for row in client.user_classifications.where(species=42):
    print(row)
result = client.user_classifications.get_all(page_size=100)
row = client.user_classifications.find(1)
client.user_classifications.export(file="user_classifications.csv")
```
