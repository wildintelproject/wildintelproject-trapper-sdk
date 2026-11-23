# Resultados agregados de clasificación

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — el mismo código en ambas. Consulta [Versiones de Trapper](versions.md).

`client.classification_results_agg` — resultados de clasificación agregados por despliegue
(recuentos, coordenadas) de un proyecto de clasificación.

**Endpoint:** `GET /media_classification/api/classifications/results/agg/{project_pk}/`.
Devuelve CSV (gzip) por defecto, o GeoJSON cuando `geojson=True`.

!!! note "No se puede usar directamente con `get()`/`where()`"
    El endpoint necesita un `project_pk` en su URL: usa `get_project_results_agg()` o
    `export_project_results_agg()`, más abajo, que resuelven la URL por ti.

## Obtener una página

```python
page = client.classification_results_agg.get_project_results_agg(project_pk=7)
for row in page.results:
    print(row.deploymentID, row.count, row.countNew)
```

## Exportar a CSV

```python
client.classification_results_agg.export_project_results_agg(
    project_pk=7, file="agg_results.csv",
)
```

`export_project_results_agg()` **solo admite CSV**: lanza `ValueError` si pasas `geojson=True`. Para la
variante GeoJSON, usa directamente `get_project_results_agg(project_pk=7, geojson=True)` (la forma de la
respuesta es distinta, así que no se envuelve como una exportación CSV).
