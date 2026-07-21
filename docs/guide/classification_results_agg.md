# Classification Results Agg

`client.classification_results_agg` — aggregated classification results per deployment
(counts, coordinates), for a classification project.

**Endpoint:** `GET /media_classification/api/classifications/results/agg/{project_pk}/`.
Returns CSV (gzip) by default, or GeoJSON when `geojson=True`.

!!! note "Not directly usable via `get()`/`where()`"
    The endpoint needs a `project_pk` in its URL — use `get_project_results_agg()`/
    `export_project_results_agg()` below, which resolve the URL for you.

## Fetching a page

```python
page = client.classification_results_agg.get_project_results_agg(project_pk=7)
for row in page.results:
    print(row.deploymentID, row.count, row.countNew)
```

## Exporting to CSV

```python
client.classification_results_agg.export_project_results_agg(
    project_pk=7, file="agg_results.csv",
)
```

`export_project_results_agg()` **only supports CSV** — it raises `ValueError` if you pass
`geojson=True`. For the GeoJSON variant, use `get_project_results_agg(project_pk=7, geojson=True)`
directly instead (the response shape differs, so it isn't wrapped as a CSV export).
