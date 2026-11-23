# Proyectos de investigación

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — el mismo código en ambas. Consulta [Versiones de Trapper](versions.md).

`client.research_projects` — proyectos de investigación de primer nivel; cada colección y cada proyecto
de clasificación pertenece exactamente a uno.

**Endpoints:**

- `GET /research/api/projects` (listado + detalle)
- `GET /research/api/project/{project_pk}/collections` (colecciones vinculadas a un proyecto)

## Filtros

| Parámetro | Tipo | Descripción |
|---|---|---|
| `owner` | bool | Solo proyectos propiedad o gestionados por el usuario actual |
| `keywords` | int repetido | Filtra por ID de palabras clave |
| `acronym` | str | Filtro exacto por acrónimo |
| `search` | str | Búsqueda de texto en nombre, acrónimo, resumen y nombre de usuario del propietario |
| `no-pagination` | cualquier valor | Desactiva la paginación en el servidor |

## Los seis patrones de acceso

```python
# Una página
page = client.research_projects.get(page=1, page_size=50)
print(page.pagination, len(page.results))

# Iteración perezosa (all() es lo mismo)
for proj in client.research_projects.where(owner=True, acronym="WINTEL"):
    print(proj)
for proj in client.research_projects.where(search="Donana"):
    print(proj)

# Exportación a CSV
client.research_projects.export(file="research_projects.csv")
```

Consulta [Uso](../usage.md) si algo de esto te resulta desconocido: es la misma interfaz en todos los componentes.

## Colecciones vinculadas a un proyecto

Cada patrón de acceso tiene una variante `_project_collections`, limitada a
`/research/api/project/{project_pk}/collections`:

```python
# Una página
cols = client.research_projects.get_project_collections(project_pk=7)
print(cols.pagination, len(cols.results))

# Iteración perezosa
for col in client.research_projects.where_project_collections(project_pk=7):
    print(col)

# Todas las páginas unidas
result = client.research_projects.get_all_project_collections(project_pk=7)

# Una única colección vinculada
col = client.research_projects.find_project_collection(project_pk=7, pk=12)
```

!!! warning "Aquí `pk` es la pk del *vínculo*, no la de la colección de almacenamiento"
    El `pk` de `find_project_collection` es la clave primaria de la fila `ResearchProjectCollection` que
    vincula este proyecto con una colección, no la pk propia de la `Collection` de almacenamiento.
    Pasar en su lugar la pk de la colección dará un 404 o devolverá la fila equivocada.

    **Cómo obtener la pk correcta:**

    - Si solo conoces el **proyecto** y la **pk de la colección de almacenamiento**, resuélvela con
      `find_collection_in_project(project_pk, collection_pk)`, más abajo: devuelve la pk del vínculo
      correspondiente, o `None` si esa colección no está vinculada al proyecto.
    - Si ya estás iterando `get_project_collections()`/`where_project_collections()`, el `.pk` de cada
      elemento **es** la pk del vínculo que necesitas, sin consulta adicional.

Comprobar si una colección de almacenamiento concreta está vinculada a un proyecto, sin conocer la pk del vínculo:

```python
link_pk = client.research_projects.find_collection_in_project(
    project_pk=7,
    collection_pk=42,
)
if link_pk:
    print(f"Collection 42 is linked via pk={link_pk}")
else:
    print("Collection 42 is not in this project")
```

Son envoltorios finos de un componente anidado, `client.research_projects.collections` (una instancia
de `ResearchProjectsCollectionsComponent`), que también puedes usar directamente si lo prefieres:

```python
for col in client.research_projects.collections.where_project(project_pk=7):
    print(col)
```
