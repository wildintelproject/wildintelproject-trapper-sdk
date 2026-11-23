# Proyectos de clasificación

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — salvo `create()`, `add_collections()` y `remove_collection()`, que son **solo v1**. Consulta [Versiones de Trapper](versions.md).

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

## Crear un proyecto de clasificación (Trapper v1)

La API REST es de solo lectura para los proyectos de clasificación, así que `create()`,
`add_collections()` y `remove_collection()` lo resuelven simulando los formularios web clásicos de
Trapper con autenticación por cookie/sesión, igual que
[`import_locations()`](locations.md#importar-localizaciones-acceso-de-escritura). En Trapper v2 lanzan
`UnsupportedVersionError`.

!!! warning "No es un contrato estable de la API"
    Dependen de formularios HTML sin versionar y requieren `user_name`/`user_password` (el *correo* de
    la cuenta en servidores que inician sesión por correo): un token por sí solo no puede
    autenticarlos.

```python
from trapper_client import ClassificationProjectCreate

project = client.classification_projects.create(
    ClassificationProjectCreate(name="Doñana 2026", research_project=3, classificator=2)
)
print(project.pk, project.name, project.status)        # 12 Doñana 2026 Ongoing
```

`create()` recibe un `ClassificationProjectCreate`, un modelo de Pydantic. Construirlo valida los datos
antes de enviar nada: un nombre y las claves primarias del research project y del clasificador. Para
construirlo desde un diccionario usa `ClassificationProjectCreate.model_validate(datos)`. El proyecto empieza *en curso* (`Ongoing`), y la cuenta que inicia sesión pasa a ser
su propietaria y administradora. El research project debe ser uno que la cuenta pueda editar; si no,
Trapper rechaza el formulario y `create()` lanza `APIError` indicando el campo:

```
Classification project creation failed (status 200): research_project: Select a valid choice. That choice is not one of the available choices.
```

Devuelve el proyecto creado, o `None` si no se puede leer de vuelta (o si se rechazó el formulario con
`raise_on_error=False`).

### Añadir colecciones

Un proyecto nuevo está vacío. `add_collections()` le vincula *colecciones de almacenamiento*:

```python
links = client.classification_projects.add_collections(project.pk, [1, 2])
print([(link.pk, link.collection_pk) for link in links])
```

- Los números que pasas son las claves primarias de las colecciones de almacenamiento
  (`Collection.pk`), como en el resto del SDK. El SDK calcula por sí solo los registros de vínculo que
  necesita Trapper.
- **Un proyecto de clasificación solo puede usar las colecciones de su research project**, y la cuenta
  debe administrar ese research project. Una colección que no esté ahí lanza `ValueError` antes de
  enviar nada. Vincular una colección a un research project es una acción web que el SDK no cubre.
- Una colección que ya está en el proyecto se deja como está, así que la llamada se puede repetir.
- Devuelve el vínculo del proyecto para cada colección.

### Quitar una colección

```python
client.classification_projects.remove_collection(project.pk, 1)    # True; False si no estaba vinculada
```

!!! danger "Borra clasificaciones"
    Desvincular es irreversible, y las clasificaciones hechas sobre esa colección **en este proyecto se
    borran junto con el vínculo**. La colección y sus recursos no se tocan.
