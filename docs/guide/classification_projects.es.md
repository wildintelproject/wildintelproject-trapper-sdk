# Proyectos de clasificación

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — el mismo código en ambas. Consulta [Versiones de Trapper](versions.md).

`client.classification_projects` — proyectos de clasificación: el espacio de trabajo donde los recursos
de una o más colecciones se clasifican con un clasificador.

**Endpoints:**

- `GET /media_classification/api/projects` (listado + detalle)
- `GET /media_classification/api/project/{project_pk}/collections` (colecciones vinculadas a un proyecto)
- `GET /media_classification/api/collection/{collection_pk}/resources/` (recursos clasificados dentro de un vínculo proyecto-colección)

## Filtros

| Parámetro | Tipo | Descripción |
|---|---|---|
| `owner` | booleano | `true` = proyectos donde el usuario es propietario, gestor o tiene *cualquier* rol |
| `status` | opción | Filtra por estado del proyecto |
| `research_project` | PK | Filtra por la clave foránea del proyecto de investigación |
| `search` | str | Busca en nombre, nombre de usuario del propietario y nombre del proyecto de investigación |

## Los seis patrones de acceso

```python
for proj in client.classification_projects.all():
    print(proj)

client.classification_projects.export(file="cs_projects.csv")
```

Consulta [Uso](../usage.md) para `get()`, `get_all()` y `find()`: es la misma interfaz que en todos los componentes.

## Colecciones vinculadas a un proyecto

La misma familia de métodos que en [Proyectos de investigación](research_projects.md#colecciones-vinculadas-a-un-proyecto),
limitada a `/media_classification/api/project/{project_pk}/collections`:

```python
page = client.classification_projects.get_project_collections(project_pk=60)
for col in client.classification_projects.where_project_collections(project_pk=60):
    print(col)
result = client.classification_projects.get_all_project_collections(project_pk=60)

col = client.classification_projects.find_project_collection(project_pk=60, pk=35)

link_pk = client.classification_projects.find_collection_in_project(
    project_pk=60, collection_pk=47,
)
```

!!! warning "Aquí `pk`/`collection_pk` es la pk del *vínculo*, no la de la colección de almacenamiento"
    La clave foránea `Classification.collection` del servidor apunta a `ClassificationProjectCollection`
    (la fila que vincula un proyecto con una colección), no a la `Collection` de almacenamiento. Esa
    fila de vínculo tiene su propia pk, y es la que esperan todos los métodos siguientes: pasar en su
    lugar la pk de la colección dará un 404 o no devolverá nada, sin avisar.

    **Cómo obtener la pk correcta:**

    - Si solo conoces el **proyecto** y la **pk de la colección de almacenamiento**, resuélvela con
      `find_collection_in_project(project_pk, collection_pk)` (arriba): recorre los vínculos del
      proyecto y devuelve la pk del vínculo correspondiente, o `None` si esa colección no está
      vinculada al proyecto.
    - Si ya estás iterando `get_project_collections()`/`where_project_collections()`, el `.pk` de cada
      elemento **es** la pk del vínculo que necesitas, sin consulta adicional.

    Esta misma pk de vínculo es también la que espera el filtro `collection=` en
    [`classifications`](classifications.md), [`ai_classifications`](ai_classifications.md),
    [`user_classifications`](user_classifications.md), [`classifications_map`](classifications_map.md)
    y [`sequences`](sequences.md). La única excepción es
    [`classification_media`](classification_media.md#medios-limitados-a-una-coleccion-dentro-del-proyecto),
    cuyo `collection_pk` *sí* es la pk real de la colección de almacenamiento: resuelve internamente
    la pk del vínculo por ti.

## Recursos clasificados dentro de un vínculo proyecto-colección

Son los datos que hay detrás del explorador de recursos de la interfaz de clasificación: recursos
clasificados (con información de secuencia y de aprobación) dentro de un vínculo proyecto-colección.

```python
page = client.classification_projects.get_collection_resources(collection_pk=35)
for res in client.classification_projects.where_collection_resources(collection_pk=35):
    print(res)
result = client.classification_projects.get_all_collection_resources(collection_pk=35)
```

### Navegación anterior/siguiente alrededor de un recurso

El servidor admite también un modo de paginación por ventana, no basado en páginas (el mismo que usa la
interfaz de clasificación para la navegación «anterior/siguiente»), que devuelve hasta `size` recursos a
cada lado de un recurso dado, ordenados por `date_recorded`:

```python
page = client.classification_projects.get_collection_resources_around(
    collection_pk=35, resource_pk=4831, size=5,
)
print(page.pagination.total, page.pagination.filtered)  # aquí no existen .count/.pages
for res in page.results:
    print(res.pk, res.name)
```
