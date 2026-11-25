# Classification Results Agg (trap rates)

!!! info "Trapper compatibility"
    **v1** ✔ · **v2** ✔ — checked against both. See [Trapper versions](versions.md).

`client.classification_results_agg` — the **trap rates** of a classification project. Trapper takes the final
classifications of the project (the ones the filters keep), adds up the count of each species per deployment and
divides it by the days the deployment worked.

**Endpoint:** `GET /media_classification/api/classifications/results/agg/{project_pk}/` — a gzip CSV, or a GeoJSON
`FeatureCollection` with `geojson=True`. The project is in the URL, so there is no `get()`/`where()`: use the
methods below.

## A row

One row per **deployment and species** (`ClassificationAgg`), with typed values (empty cells are `None`):

| Fields | What |
|---|---|
| `deploymentID`, `locationID`, `locationName`, `latitude`, `longitude`, `coordinateUncertainty` | Where |
| `deploymentStart`, `deploymentEnd` (`datetime`), `days` | When, and the days it worked |
| `setupBy`, `cameraID`, `cameraModel`, `cameraDelay`, `cameraHeight`, `cameraDepth`, `cameraTilt`, `cameraHeading`, `detectionDistance`, `timestampIssues`, `baitUse`, `featureType`, `habitat`, `deploymentGroups`, `deploymentTags`, `deploymentComments` | The deployment's Camtrap DP fields |
| `observationType`, `scientificName` | What was seen (`None` for a deployment with no observation, with `all_dep=True`) |
| `count` (or `countNew`) | How many |
| `trapRate` | `count / days` |

Deployments without start or end date are left out.

```python
page = client.classification_results_agg.get_project_results_agg(project_pk=7)
for row in page.results:
    print(row.deploymentID, row.scientificName, row.count, row.trapRate)
```

Trapper sends the whole table at once (`page` and `page_size` do nothing). With no rows it answers
`400 "Empty queryset"`; the SDK gives no rows (an empty list, an empty `FeatureCollection` or an empty file).

## Parameters and filters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `count_var` | `"count"` / `"countNew"` | `"count"` | What is added up. `countNew` only if the classificator has it (`400` otherwise) |
| `all_dep` | boolean | `False` | Every deployment of the project, also the ones with no observation |
| `filter_dep` | text | | Only deployments whose `deploymentID` contains it |

The filters are those of the results table of [classification results](classifications.md): `approved` (sent as
`status` on v1), `species`, `observation_type`, `deployment`, `collection`, `rdate_from`/`rdate_to`, `ftype`,
`bboxes`, ... Trapper ignores any other without an error; the SDK emits an `UnknownFilterWarning`.
`classified`/`classified_ai` answer `500` on v2 (the SDK warns).

```python
client.classification_results_agg.get_project_results_agg(7, approved=True, species=[3, 5], filter_dep="don")
```

## GeoJSON

```python
fc = client.classification_results_agg.get_project_geojson(7, approved=True)
for feature in fc["features"]:
    print(feature["geometry"]["coordinates"], feature["properties"]["trapRate"])
```

One point per row, with the row's fields (without `latitude` and `longitude`) as properties.
`get_project_results_agg(geojson=True)` is a `ValueError`: it gives a `FeatureCollection`, not rows.

## Exporting to CSV

```python
client.classification_results_agg.export_project_results_agg(project_pk=7, file="trap_rates.csv")
# Trapper's CSV as it comes (its header and column order)
client.classification_results_agg.export_project_results_agg(project_pk=7, file="trap_rates.csv", raw=True)
```
