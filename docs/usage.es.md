# Uso

## Crear un cliente

Autenticación con un token estático:

```python
from trapper_client import TrapperClient

client = TrapperClient(
    base_url="https://your-trapper.example",
    access_token="<token>",
)
```

O con usuario y contraseña:

```python
client = TrapperClient(
    base_url="https://your-trapper.example",
    user_name="user",
    user_password="password",
)
```

Cada recurso está disponible como atributo de `client`: `client.locations`, `client.deployments`,
`client.classification_results`, etc. (la lista completa está en la página de [Inicio](index.md#recursos-disponibles)).
Todos comparten exactamente la misma interfaz que se describe a continuación, porque la heredan de la
misma clase base (`TrapperComponent`). Aprenderla una vez significa que ya sabes usar todos los
componentes del SDK.

Con `trapper_version="auto"` (el valor por defecto) el cliente detecta si el servidor es Trapper v1 o
v2; consulta [Versiones de Trapper](guide/versions.md).

---

## Los seis patrones de acceso

Todos los componentes exponen los mismos seis métodos. Se diferencian solo en *cuántos* datos traen y
*cuándo*:

| Método | Devuelve | Úsalo cuando... |
|---|---|---|
| `get(page=1, page_size=50, **filters)` | Una página `PaginatedResult` | Quieres una página concreta, p. ej. para construir tu propia paginación |
| `get_all(page_size=100, **filters)` | Un `PaginatedResult` con *todos* los elementos unidos | Quieres todo de una vez y cabe cómodamente en memoria |
| `where(**filters)` | Iterador perezoso `APIQuery` | Quieres recorrer los elementos página a página, sin cargarlos todos de entrada |
| `all(**filters)` | Igual que `where()`: es un simple alias | Solo quieres leer «recorre todo este recurso» |
| `find(pk)` | Una instancia de modelo tipada | Ya conoces la clave primaria |
| `export(file=..., **filters)` | `Path` a un CSV, o `list[Model]` si `file=None` | Quieres volcar a CSV, o instancias de modelo sin gestionar paginación |

Cada argumento `**filters` se convierte en un parámetro de la query string enviada al servidor; cuáles
se aceptan depende del componente (consulta la página de cada componente en **Guías de componentes**).

### `get()` — una página

```python
page = client.locations.get(page=1, page_size=25)

print(page.pagination.count)   # total de elementos en el servidor
print(page.pagination.pages)   # número total de páginas
for loc in page.results:
    print(loc.pk, loc.name)
```

Pasa argumentos adicionales para filtrar los resultados:

```python
page = client.deployments.get(page=1, page_size=50, research_project=3)
```

### `get_all()` — todas las páginas, unidas

`get_all()` llama a `get()` repetidamente y une todas las páginas en un único `PaginatedResult`. Es
cómodo, pero carga todo en memoria antes de devolver.

```python
result = client.research_projects.get_all(page_size=100)
print(len(result.results), "projects")
```

### `where()` y `all()` — iteración perezosa

`where()` devuelve un [`APIQuery`](api/api_query.md): las páginas se piden bajo demanda mientras
iteras, así que el uso de memoria se mantiene constante sea cual sea el número de elementos del
servidor.

```python
for loc in client.locations.where(page_size=100):
    print(loc.pk, loc.name)
```

`all()` es exactamente el mismo método con otro nombre; usa el que se lea mejor en cada caso:

```python
for loc in client.locations.all():
    print(loc.pk, loc.name)
```

Ambos aceptan los mismos argumentos: filtros de consulta como palabras clave, más un `filter_fn`
aplicado en el cliente:

```python
active = client.deployments.where(
    page_size=50,
    filter_fn=lambda d: d.end_date is None,
)
for dep in active:
    print(dep.pk)
```

Y ambos pueden usarse como gestor de contexto para parar antes sin agotar el iterador:

```python
with client.locations.where(page_size=50) as query:
    first_ten = [next(query) for _ in range(10)]
```

### `find()` — un elemento por su PK

```python
loc = client.locations.find(42)
print(loc.name, loc.coordinates)
```

### `export()` — volcar a CSV (o recibir modelos)

`export()` escribe todos los resultados en un CSV y devuelve la ruta:

```python
path = client.locations.export(file="locations.csv")
print(f"Saved to {path}")
```

El CSV se escribe con los nombres de columna del SDK (`pk`, `location_id`, ...), ordenadas
alfabéticamente. Para guardar el fichero **tal como lo envía Trapper**, con su cabecera, el orden de sus
columnas y sus valores (`locationID`, `_id`, `ignoreDST`, ...), pasa `raw=True` (necesita `file`, y
`validate` no se aplica):

```python
client.locations.export(file="locations.csv", raw=True)
```

Pasa `file=None` para recibir una lista de instancias de modelo, sin CSV de por medio: simplemente
todos los elementos descargados y parseados:

```python
records = client.deployments.export(file=None)
```

Algunos componentes validan o exportan un esquema *distinto* al que usan `get()`/`where()` (por
ejemplo, filas con formato CamtrapDP en lugar del formato interno de Trapper). Es el `export_schema`, y
se documenta en la página de cada componente cuando aplica.

---

## Más allá de los seis patrones: métodos propios de cada componente

Varios componentes añaden sus propios métodos a los seis anteriores, porque su endpoint necesita algo
que la interfaz genérica no puede expresar: un recurso anidado bajo otro
(`client.classification_media.get_project_media(project_pk=7)`), una operación de escritura que
simula la interfaz web clásica (`client.locations.import_locations(...)`) o una respuesta no paginada
(`client.classification_package.get_project_package(...)`). Se explican uno a uno en **Guías de
componentes**; empieza por ahí cuando sepas *qué* recurso necesitas. Esta página trata de la mecánica
que todos comparten.

!!! warning "`collection_pk` no siempre significa lo mismo"
    Algunos de esos métodos específicos aceptan un `collection_pk` (o un filtro `collection=`) que
    **no** es la pk de la colección de almacenamiento, sino la de una tabla intermedia de enlace
    (`ClassificationProjectCollection` o `ResearchProjectCollection`), porque a eso apunta realmente
    la clave foránea `Classification.collection` del servidor. El nombre del parámetro es el mismo en
    ambos casos, así que es fácil pasar la pk equivocada sin ningún error hasta que los resultados
    llegan vacíos. Consulta [Proyectos de clasificación](guide/classification_projects.md#recursos-clasificados-dentro-de-un-vinculo-proyecto-coleccion)
    y [Proyectos de investigación](guide/research_projects.md#colecciones-vinculadas-a-un-proyecto) para
    saber qué métodos esperan qué pk y cómo obtener una a partir de la otra.

---

## Resultados de clasificación — un ejemplo completo

Obtener resultados paginados de un proyecto de clasificación:

```python
page = client.classification_results.get_project_results(
    project_pk=7,
    page=1,
    page_size=50,
    approved=True,
)
for row in page.results:
    print(row.observationID, row.scientificName)
```

Exportar todos los resultados de un proyecto directamente a CSV:

```python
client.classification_results.export_project_results(
    project_pk=7,
    file="observations.csv",
)
```

Iterar de forma perezosa:

```python
for row in client.classification_results.where_project_results(project_pk=7):
    print(row)
```

Consulta la [guía de Clasificaciones](guide/classifications.md) para ver el panorama completo,
incluido `import_classifications()`.

---

## Pasar objetos donde va una clave primaria

Todos los parámetros `*_pk` (y el `pk` de `find()`) aceptan la clave primaria como `int` —o un texto numérico— y
también el objeto del SDK al que corresponde, tal como lo devuelven los métodos:

```python
proyecto = client.classification_projects.find(2)
client.classification_results.get_project_results(proyecto)        # igual que get_project_results(2)
enlace = client.classification_projects.get_all_project_collections(proyecto).results[0]
client.classification_projects.get_all_collection_resources(enlace)  # el enlace, un ClassificationProjectCollection
client.resources.get_all_by_location(client.locations.find(27))
```

Las firmas dicen qué objetos acepta cada uno (`project_pk: int | ClassificationProject`). Un objeto de otro tipo
—un `ClassificationProject` donde va un proyecto de investigación— es un `TypeError` antes de ninguna petición.

## Endpoint genérico

Para cualquier endpoint que no cubra un componente, usa `client.where()` directamente:

```python
for item in client.where("api/deployments/", query={"research_project": 7}):
    print(item)
```
