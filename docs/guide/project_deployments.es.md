# Despliegues de proyecto (Trapper v2)

Trapper v2 sirve los despliegues de un **proyecto de clasificación** en `api/deployments/<slug>/`,
junto con las acciones sobre ellos. El SDK lo envuelve como `client.project_deployments`; en un
servidor v1 todos sus métodos lanzan `UnsupportedVersionError`.

`<slug>` es el `slug` del proyecto, y el proyecto debe ser de Ciencia Ciudadana (público o privado) y
tener un clasificador; cualquier otro slug responde `404`. Todos los métodos reciben el slug en primer
lugar.

```python
slug = "mamiferos-donana-sm"

for dep in client.project_deployments.where(slug):
    print(dep.deployment_id, dep.location_name, [s.latin_name for s in dep.species])

client.project_deployments.locations(slug)             # localizaciones con su número de despliegues
dep = client.project_deployments.find(slug, 3)         # el registro completo y editable
```

## Lectura

| Método | Devuelve |
|---|---|
| `get(slug, page=, page_size=, **filters)` | `PaginatedResult[ProjectDeployment]` |
| `where(slug, **filters)` | `APIQuery[ProjectDeployment]` perezoso |
| `locations(slug)` | `list[ProjectLocation]` |
| `find(slug, pk)` | `ProjectDeploymentDetail` |
| `progress(slug, pk)` | `ProjectDeploymentProgress` (`running`, `stages`): progreso del pipeline de IA |
| `calibration_results(slug, pk)` | filas sin procesar; vacío hasta que se ejecute una calibración |

El listado solo contiene los despliegues que puedes ver: los que posees o gestionas, los públicos, los
compartidos a través de un equipo y todos si tu rol en el proyecto puede ver clasificaciones.

## Modificar un despliegue

```python
client.project_deployments.update(slug, 3, comments="Camera moved 2 m north")   # PATCH
client.project_deployments.update_timestamps(slug, 3, time_offset=-3600)        # el reloj iba 1 h adelantado
client.project_deployments.delete(slug, 3)                                       # irreversible
```

* `update()` necesita `can_update`; `delete()` necesita `can_delete` (ambos son indicadores de cada fila).
* **Trapper reescribe `deployment_id` al guardar un despliegue** (le añade el código de la
  localización, p. ej. `don01-2024a` → `don01-2024a-don-01`), sea cual sea el campo que cambies.
* `update_timestamps()` desplaza la fecha registrada de *todos* los recursos del despliegue en
  `time_offset` segundos; las fechas de las clasificaciones se sincronizan mediante una tarea en
  segundo plano.

## Calibración con IA

`request_depth_calibration()` y `request_distance_estimation()` lanzan trabajos en los modelos de IA
del proyecto y responden `400` cuando el proyecto no tiene ninguno configurado. Están envueltos a
partir del código fuente de Trapper, pero solo se han probado con simulaciones: los servidores de
prueba no tienen IA desplegada.

## Véase también

Para los despliegues en bloque (importación, exportación, GeoJSON) consulta [Despliegues](deployments.md).
