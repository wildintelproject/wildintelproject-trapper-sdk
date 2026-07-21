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
| [Classifications](schemas/classifications.md) | `ClassificationRecord`, `ClassificationProject`, etc. |
| [AI Classifications](schemas/ai_classifications.md) | `AIClassificationRecord`, `AIClassificationRecordExport*` |
| [User Classifications](schemas/user_classifications.md) | `UserClassificationRecord`, `ResourceUser`, `UserObservationAttr` |
| [Classifications Map](schemas/classifications_map.md) | `ClassificationMapRecord`, `ResourceClassificationMap` |
| [Classificators](schemas/classificators.md) | `ClassificatorRecord` |
| [Species](schemas/species.md) | `SpeciesRecord` |
| [Maps](schemas/maps.md) | `MapRecord` |
| [Sequences](schemas/sequences.md) | `SequenceRecord` |
| [Users](schemas/users.md) | `UserRecord` |

## Errores

| Clase | Descripción |
|-------|-------------|
| [`APIError` y subclases](errors.md) | Excepciones de la API |
