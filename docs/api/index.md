# API Reference

Referencia completa de la API pública de `trapper_client`.

## Cliente principal

| Clase | Descripción |
|-------|-------------|
| [`TrapperClient`](trapper_client.md) | Cliente de alto nivel para la API de Trapper |
| [`APIClientBase`](api_client_base.md) | Cliente HTTP base con autenticación |
| [`APIQuery`](api_query.md) | Iterador lazy sobre endpoints paginados |
| [`TrapperComponent`](base_component.md) | Clase base para todos los componentes |

## Componentes

| Clase | Recurso |
|-------|---------|
| [`LocationsComponent`](components/locations.md) | `/geomap/api/locations` |
| [`LocationsGeoJsonComponent`](components/locations_geojson.md) | `/geomap/api/locations/geojson/` |
| [`DeploymentsComponent`](components/deployments.md) | `/geomap/api/deployments` |
| [`ResourcesComponent`](components/resources.md) | `/storage/api/resources` |
| [`CollectionsComponent`](components/collections.md) | `/storage/api/collections` (incluye `_ondemand`, `_map`, `_append`) |
| [`ResearchProjectsComponent`](components/research_projects.md) | `/research/api/projects` |
| [`ResearchProjectsCollectionsComponent`](components/research_project_collections.md) | `/research/api/project/{pk}/collections` |
| [`ClassificationProjectsComponent`](components/classification_projects.md) | `/media_classification/api/projects` (incluye `/project/{pk}/collections`) |
| [`ClassificationsComponent`](components/classifications.md) | `/media_classification/api/classifications` |
| [`AIClassificationsComponent`](components/ai_classifications.md) | `/media_classification/api/ai-classifications` |
| [`UserClassificationsComponent`](components/user_classifications.md) | `/media_classification/api/user-classifications` |
| [`ClassificationsMapComponent`](components/classifications_map.md) | `/media_classification/api/classifications_map` |
| [`ClassificatorsComponent`](components/classificators.md) | `/media_classification/api/classificators` |
| [`ClassificationMediaComponent`](components/classification_media.md) | `/media_classification/api/media/{project_pk}/` |
| [`ClassificationResultsAggComponent`](components/classification_results_agg.md) | `/media_classification/api/classifications/results/agg/{project_pk}/` |
| [`ClassificationPackageComponent`](components/classification_package.md) | `/media_classification/api/package/{project_pk}/` |
| [`SpeciesComponent`](components/species.md) | `/tables/api/species` |
| [`MapsComponent`](components/maps.md) | `/geomap/api/maps` |
| [`SequencesComponent`](components/sequences.md) | `/media_classification/api/sequences` |
| [`UsersComponent`](components/users.md) | `/accounts/api/users` |

## Schemas

| Módulo | Contenido |
|--------|-----------|
| [Common](schemas/common.md) | `TrapperSchema`, `PaginatedResult`, `Pagination` |
| [Locations](schemas/locations.md) | `Location`, `LocationExport`, `LocationGeoJson*` |
| [Deployments](schemas/deployments.md) | `Deployment`, `DeploymentExport` |
| [Resources](schemas/resources.md) | `Resource` |
| [Collections](schemas/collections.md) | `Collection` |
| [Research Projects](schemas/research_projects.md) | `ResearchProject`, `ResearchProjectCollection` |
| [Classifications](schemas/classifications.md) | `Classification`, `ClassificationProject`, etc. |
| [AI Classifications](schemas/ai_classifications.md) | `AIClassification`, `AIClassificationRecordExport*` |
| [User Classifications](schemas/user_classifications.md) | `UserClassification`, `ResourceUser`, `UserObservationAttr` |
| [Classifications Map](schemas/classifications_map.md) | `ClassificationMap`, `ResourceClassificationMap` |
| [Classificators](schemas/classificators.md) | `Classificator` |
| [Species](schemas/species.md) | `Species` |
| [Maps](schemas/maps.md) | `Map` |
| [Sequences](schemas/sequences.md) | `Sequence` |
| [Users](schemas/users.md) | `User` |

## Errores

| Clase | Descripción |
|-------|-------------|
| [`APIError` y subclases](errors.md) | Excepciones de la API |

## Renamed schemas

The schemas that Trapper's API returns are named after the resource, without the `Record` suffix some
of them used to carry. The old names still import, give the same class and warn with a
`DeprecationWarning`; they will be removed in a future release.

| Old name | New name |
|----------|----------|
| `UserRecord` | `User` |
| `SpeciesRecord` | `Species` |
| `SequenceRecord` | `Sequence` |
| `MapRecord` | `Map` |
| `ClassificatorRecord` | `Classificator` |
| `ClassificationRecord` | `Classification` |
| `UserClassificationRecord` | `UserClassification` |
| `AIClassificationRecord` | `AIClassification` |
| `ClassificationMapRecord` | `ClassificationMap` |
| `ClassificationAggRecord` | `ClassificationAgg` |
| `ClassificationResourceRecord` | `ClassifiedResource` (`ClassificationResource` is already the resource embedded in a classification) |
| `MediaRecord` | `Media` |

The export row schemas (`ClassificationRecordExport`, `ClassificationResultRecordCamtrapDP`, ...) keep
their names: they describe a row of an exported file.

`Sequence` has the same name as `typing.Sequence`; if a module uses both, import one under another
name (`from trapper_client import Sequence as TrapperSequence`).
