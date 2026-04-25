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
| [`LocationsGeoJsonComponent`](components/locations_geojson.md) | `/geomap/api/locations/geojson` |
| [`DeploymentsComponent`](components/deployments.md) | `/geomap/api/deployments` |
| [`ResourcesComponent`](components/resources.md) | `/storage/api/resources` |
| [`CollectionsComponent`](components/collections.md) | `/storage/api/collections` |
| [`ResearchProjectsComponent`](components/research_projects.md) | `/storage/api/research_projects` |
| [`ResearchProjectsCollectionsComponent`](components/research_project_collections.md) | `/storage/api/research_projects/{pk}/collections` |
| [`ClassificationProjectsComponent`](components/classification_projects.md) | `/media_classification/api/projects` |
| [`ClassificationProjectsCollectionsComponent`](components/classification_project_collections.md) | `/media_classification/api/project/{pk}/collections` |
| [`ClassificationsComponent`](components/classifications.md) | `/media_classification/api/classifications` |
| [`AIClassificationsComponent`](components/ai_classifications.md) | `/media_classification/api/ai_classifications` |
| [`ClassificationMediaComponent`](components/classification_media.md) | `/media_classification/api/media` |
| [`ClassificationResultsAggComponent`](components/classification_results_agg.md) | `/media_classification/api/classifications/results/agg` |
| [`ClassificationPackageComponent`](components/classification_package.md) | `/media_classification/api/classifications/results/package` |

## Schemas

| Módulo | Contenido |
|--------|-----------|
| [Common](schemas/common.md) | `TrapperSchema`, `PaginatedResult`, `Pagination` |
| [Locations](schemas/locations.md) | `Location`, `LocationExport`, `LocationGeoJson*` |
| [Deployments](schemas/deployments.md) | `Deployment`, `DeploymentExport` |
| [Resources](schemas/resources.md) | `Resource` |
| [Collections](schemas/collections.md) | `Collection`, `CollectionCP` |
| [Research Projects](schemas/research_projects.md) | `ResearchProject`, `ResearchProjectCollection` |
| [Classifications](schemas/classifications.md) | `ClassificationRecord`, `ClassificationProject`, etc. |
| [AI Classifications](schemas/ai_classifications.md) | `AIClassificationRecord`, `AIClassificationRecordExport*` |

## Errores

| Clase | Descripción |
|-------|-------------|
| [`APIError` y subclases](errors.md) | Excepciones de la API |
