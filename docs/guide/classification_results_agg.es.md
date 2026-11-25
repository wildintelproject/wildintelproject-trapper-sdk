# Resultados agregados de clasificación (tasas de captura)

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — comprobado en los dos. Consulta [Versiones de Trapper](versions.md).

`client.classification_results_agg` — las **tasas de captura** de un proyecto de clasificación. Trapper toma las
clasificaciones finales del proyecto (las que dejan pasar los filtros), suma el recuento de cada especie por
despliegue y lo divide entre los días que funcionó el despliegue.

**Endpoint:** `GET /media_classification/api/classifications/results/agg/{project_pk}/` — un CSV en gzip, o un
`FeatureCollection` GeoJSON con `geojson=True`. El proyecto va en la URL, así que no hay `get()`/`where()`: usa los
métodos de abajo.

## Una fila

Una fila por **despliegue y especie** (`ClassificationAgg`), con valores tipados (las celdas vacías son `None`):

| Campos | Qué |
|---|---|
| `deploymentID`, `locationID`, `locationName`, `latitude`, `longitude`, `coordinateUncertainty` | Dónde |
| `deploymentStart`, `deploymentEnd` (`datetime`), `days` | Cuándo, y los días que funcionó |
| `setupBy`, `cameraID`, `cameraModel`, `cameraDelay`, `cameraHeight`, `cameraDepth`, `cameraTilt`, `cameraHeading`, `detectionDistance`, `timestampIssues`, `baitUse`, `featureType`, `habitat`, `deploymentGroups`, `deploymentTags`, `deploymentComments` | Los campos Camtrap DP del despliegue |
| `observationType`, `scientificName` | Qué se vio (`None` en un despliegue sin observaciones, con `all_dep=True`) |
| `count` (o `countNew`) | Cuántos |
| `trapRate` | `count / days` |

Se excluyen los despliegues sin fecha de inicio o de fin.

```python
page = client.classification_results_agg.get_project_results_agg(project_pk=7)
for row in page.results:
    print(row.deploymentID, row.scientificName, row.count, row.trapRate)
```

Trapper envía la tabla entera de una vez (`page` y `page_size` no hacen nada). Sin filas responde
`400 "Empty queryset"`; el SDK no devuelve filas (una lista vacía, un `FeatureCollection` vacío o un fichero vacío).

## Parámetros y filtros

| Parámetro | Tipo | Por defecto | Descripción |
|---|---|---|---|
| `count_var` | `"count"` / `"countNew"` | `"count"` | Qué se suma. `countNew` solo si el clasificador lo tiene (`400` si no) |
| `all_dep` | booleano | `False` | Todos los despliegues del proyecto, también los que no tienen observaciones |
| `filter_dep` | texto | | Solo los despliegues cuyo `deploymentID` lo contiene |

Los filtros son los de la tabla de resultados de [resultados de clasificación](classifications.md): `approved` (se
envía como `status` en v1), `species`, `observation_type`, `deployment`, `collection`, `rdate_from`/`rdate_to`,
`ftype`, `bboxes`, ... Trapper ignora sin error cualquier otro; el SDK emite un `UnknownFilterWarning`.
`classified`/`classified_ai` responden `500` en v2 (el SDK avisa).

```python
client.classification_results_agg.get_project_results_agg(7, approved=True, species=[3, 5], filter_dep="don")
```

## GeoJSON

```python
fc = client.classification_results_agg.get_project_geojson(7, approved=True)
for feature in fc["features"]:
    print(feature["geometry"]["coordinates"], feature["properties"]["trapRate"])
```

Un punto por fila, con los campos de la fila (sin `latitude` ni `longitude`) como propiedades.
`get_project_results_agg(geojson=True)` es un `ValueError`: da un `FeatureCollection`, no filas.

## Exportar a CSV

```python
client.classification_results_agg.export_project_results_agg(project_pk=7, file="tasas.csv")
# El CSV de Trapper tal cual llega (su cabecera y su orden de columnas)
client.classification_results_agg.export_project_results_agg(project_pk=7, file="tasas.csv", raw=True)
```
