# Classifications Map

`client.classifications_map` — resources pending classification for a given project, as used to
drive the classification UI's map/queue view.

**Endpoint:** `GET /media_classification/api/classifications_map` (list + detail).

## Filters

| Parameter | Type | Description |
|---|---|---|
| `project` | PK | Filter by classification project PK |
| `owner` | boolean | `true` = resources where user is owner/manager |
| `deployment` | list of PKs | Filter by deployment PKs |
| `collection` | list of PKs | Filter by collection PKs |
| `locations_map` | comma-separated PKs | Filter by location PKs |
| `rdate_from` / `rdate_to` | date | `date_recorded` range |
| `rtime_from` / `rtime_to` | HH:MM | Time-of-day range |
| `ftype` | choice | Resource type (IMAGE, VIDEO, ...) |
| `classified` | boolean | Classified by humans |
| `classified_ai` | boolean | Classified by AI |
| `approved` | boolean | Has a FINAL approved classification |
| `species` | list of PKs | Filter by species PKs |
| `observation_type` | choice | Filter by observation type |

## The six access patterns

This component has no special methods — it's exactly the generic interface described in
[Usage](../usage.md):

```python
page = client.classifications_map.get(page=1, page_size=50, project=7)
for row in client.classifications_map.where(project=7, classified=False):
    print(row)
result = client.classifications_map.get_all(project=7)
row = client.classifications_map.find(1)
client.classifications_map.export(file="classifications_map.csv")
```
