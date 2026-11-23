# Proyectos de investigación

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — salvo `create()`, que es **solo v1**. Consulta [Versiones de Trapper](versions.md).

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

## Crear un proyecto de investigación (Trapper v1)

La API REST es de solo lectura para los proyectos de investigación, así que `create()` lo resuelve
simulando el formulario web clásico `research/project/create/` con autenticación por cookie/sesión,
igual que [`import_locations()`](locations.md#importar-localizaciones-acceso-de-escritura). La cuenta
que inicia sesión pasa a ser la propietaria y administradora del proyecto. En Trapper v2 lanza
`UnsupportedVersionError`.

!!! warning "No es un contrato estable de la API"
    Depende de un formulario HTML sin versionar y requiere `user_name`/`user_password` (el *correo* de
    la cuenta en servidores que inician sesión por correo): un token por sí solo no puede autenticarlo.

```python
from trapper_client import BaitUse, ResearchProjectCreate, SamplingDesign

project = client.research_projects.create(
    ResearchProjectCreate(
        name="Doñana mammals",
        acronym="DONMAM",                       # de 3 a 10 caracteres; nombre y acrónimo son únicos
        sampling_design=SamplingDesign.TARGETED,
        bait_use=BaitUse.SCENT,
        keywords=["camera trap", "mammals"],
        abstract="Medium and large mammals of Doñana National Park.",
    )
)
print(project.pk, project.name)
```

`create()` recibe un `ResearchProjectCreate`, un modelo de Pydantic con todos los campos del
formulario de creación. Construirlo valida los datos antes de enviar nada: recorta los textos, rechaza
los campos desconocidos (una errata falla en lugar de ignorarse) y lanza `pydantic.ValidationError`,
que es un `ValueError`, indicando el campo incorrecto. Para construirlo desde un diccionario (un JSON o
un YAML, por ejemplo) usa `ResearchProjectCreate.model_validate(datos)`.

| Campo | Valores | Por defecto |
|---|---|---|
| `name` | hasta 255 caracteres, único | obligatorio |
| `acronym` | de 3 a 10 caracteres, único | obligatorio |
| `sampling_design` | `SamplingDesign`: `simpleRandom` (1), `systematicRandom` (2), `clusteredRandom` (3), `experimental` (4), `targeted` (5), `opportunistic` (6) | `1` |
| `sensor_method` | `SensorMethod`: `activityDetection` (1), `timeLapse` (2), `both` (3) | `1` |
| `animal_types` | `AnimalTypes`: `unmarked` (1), `marked` (2), `both` (3) | `1` |
| `bait_use` | `BaitUse`: `none` (1), `scent` (2), `food` (3), `visual` (4), `acoustic` (5), `other` (6) | `1` |
| `event_interval` | segundos, `0` o más | `0` |
| `keywords` | lista de textos; una palabra clave puede llevar espacios y comas, pero no comillas dobles | vacía |
| `abstract`, `methods`, `description` | texto libre, hasta 2000 caracteres cada uno | ninguno |

Los cuatro campos de opción tienen una enumeración en `trapper_client`. Sus miembros son los enteros que
guarda Trapper y llevan la etiqueta que muestra, así que el editor puede autocompletarlos. El campo
acepta el miembro, su número o su etiqueta, y cualquier otra cosa se rechaza con la lista de valores
válidos:

```python
BaitUse.SCENT            # <BaitUse.SCENT: 2>
BaitUse.SCENT.label      # "scent"
ResearchProjectCreate(name="N", acronym="ABC", bait_use="scent")    # igual que BaitUse.SCENT o 2
```

### Miembros

Quien crea el proyecto pasa a ser su administrador. `members` añade a los demás usuarios que se unen,
cada uno con un rol:

```python
from trapper_client import ResearchProjectCreate, ResearchProjectMember, ResearchProjectRoleType

ana = next(iter(client.users.where(search="ana")))

project = client.research_projects.create(
    ResearchProjectCreate(
        name="Doñana mammals",
        acronym="DONMAM",
        members=[
            ResearchProjectMember(user=ana, role=ResearchProjectRoleType.EXPERT),
            ResearchProjectMember(user=7, role="collaborator"),
        ],
    )
)
print([(r.username, r.roles) for r in project.project_roles])
# [('ana', ['Expert']), ('rp_staff', ['Admin']), ('user7', ['Collaborator'])]
```

- `user` es el `User` que devuelve `client.users`, o su clave primaria.
- `role` es un `ResearchProjectRoleType` (`ADMIN`, `EXPERT` o `COLLABORATOR`), su número o su
  etiqueta, en cualquier caso.
- Un usuario no puede aparecer dos veces (el modelo lo rechaza), y la cuenta que crea el proyecto no
  puede figurar: ya es la administradora. Las dos cosas fallan antes de enviar nada. Un usuario que no
  existe lo rechaza Trapper, indicando la fila (`project_roles-1-user: Select a valid choice.`).
- Los miembros solo se pueden dar **al crear el proyecto**: cambiar los roles de un proyecto ya creado es
  una acción web que el SDK no cubre.

### Qué devuelve

- **Una cuenta staff:** el proyecto se activa al instante y `create()` lo devuelve.
- **Cualquier otra cuenta:** Trapper crea el proyecto pero lo deja *sin aprobar*, y lo oculta de la API
  hasta que un administrador lo apruebe. Entonces `create()` devuelve `None`: el proyecto existe, solo
  que todavía no se puede leer.

### Cuando el servidor rechaza el formulario

Un nombre o acrónimo ya en uso, o un acrónimo de longitud incorrecta, hace que Trapper vuelva a mostrar
el formulario (estado `200`). `create()` lanza `APIError` indicando el campo:

```
Research project creation failed (status 200): name: Research project with this Name already exists.
```

Pasa `raise_on_error=False` para recibir `None` en su lugar. Lo que el modelo puede comprobar en local
(nombre vacío, longitud del acrónimo, una opción desconocida, ...) lanza `ValidationError` antes de
enviar nada.
