# Project deployments (Trapper v2)

Trapper v2 serves the deployments of a **classification project** under `api/deployments/<slug>/`,
together with the actions on them. The SDK wraps it as `client.project_deployments`; on a v1 server
every method raises `UnsupportedVersionError`.

`<slug>` is the project's `slug`, and the project must be a Citizen Science one (public or private)
with a classificator; any other slug answers `404`. All methods take the slug first.

```python
slug = "mamiferos-donana-sm"

for dep in client.project_deployments.where(slug):
    print(dep.deployment_id, dep.location_name, [s.latin_name for s in dep.species])

client.project_deployments.locations(slug)             # locations with their deployment count
dep = client.project_deployments.find(slug, 3)         # the full, editable record
```

## Reading

| Method | Returns |
|---|---|
| `get(slug, page=, page_size=, **filters)` | `PaginatedResult[ProjectDeployment]` |
| `where(slug, **filters)` | lazy `APIQuery[ProjectDeployment]` |
| `locations(slug)` | `list[ProjectLocation]` |
| `find(slug, pk)` | `ProjectDeploymentDetail` |
| `progress(slug, pk)` | `ProjectDeploymentProgress` (`running`, `stages`) — AI pipeline progress |
| `calibration_results(slug, pk)` | raw rows; empty until a calibration ran |

The listing only contains the deployments you may see: the ones you own or manage, public ones, those
shared through a team, and all of them if your role in the project can view classifications.

## Changing a deployment

```python
client.project_deployments.update(slug, 3, comments="Camera moved 2 m north")   # PATCH
client.project_deployments.update_timestamps(slug, 3, time_offset=-3600)        # clock was 1 h ahead
client.project_deployments.delete(slug, 3)                                       # irreversible
```

* `update()` needs `can_update`; `delete()` needs `can_delete` (both are flags on each row).
* **Trapper rewrites `deployment_id` when it saves a deployment** (it appends the location code, e.g.
  `don01-2024a` → `don01-2024a-don-01`), whichever field you change.
* `update_timestamps()` shifts the recorded date of *every* resource of the deployment by
  `time_offset` seconds; the classifications' dates are synchronised by a background task.

## AI calibration

`request_depth_calibration()` and `request_distance_estimation()` start jobs on the project's AI
models and answer `400` when the project has none configured. They are wrapped from Trapper's
source, but have only been exercised against mocks: the test servers have no AI deployed.

## See also

For deployments in bulk (import, export, GeoJSON) see [Deployments](deployments.md).
