# Clasificadores

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — salvo `create()`, que es **solo v1**. Consulta [Versiones de Trapper](versions.md).

`client.classificators` — configuraciones de clasificador (el esquema de taxonomía y atributos con el
que un proyecto de clasificación clasifica).

**Endpoint:** `GET /media_classification/api/classificators` (listado + detalle).

## Filtros

| Parámetro | Tipo | Descripción |
|---|---|---|
| `owner` | booleano | `true` = clasificadores del usuario |
| `search` | cadena | Búsqueda por nombre o descripción |

## Los seis patrones de acceso

Este componente no tiene métodos especiales: es exactamente la interfaz genérica descrita en
[Uso](../usage.md):

```python
page = client.classificators.get(page=1, page_size=50)
for classificator in client.classificators.where(owner=True):
    print(classificator)
result = client.classificators.get_all()
classificator = client.classificators.find(1)
client.classificators.export(file="classificators.csv")
```

## Crear un clasificador (Trapper v1)

La API REST es de solo lectura para los clasificadores, así que `create()` lo resuelve simulando el
formulario web clásico `media_classification/classificator/create/` con autenticación por cookie/sesión,
igual que [`import_locations()`](locations.md#importar-localizaciones-acceso-de-escritura). La cuenta que
inicia sesión pasa a ser la propietaria. En Trapper v2 lanza `UnsupportedVersionError`.

!!! warning "No es un contrato estable de la API"
    Depende de un formulario HTML sin versionar y requiere `user_name`/`user_password` (el *correo* de la
    cuenta en servidores que inician sesión por correo): un token por sí solo no puede autenticarlo.

```python
from trapper_client import ClassificatorCreate

lynx = next(iter(client.species.where(search="lynx")))
classificator = client.classificators.create(
    ClassificatorCreate(
        name="Iberian mammals",
        species=[lynx, 5, 6, 7, 8],     # entre las que elige quien clasifica: objetos o claves primarias
        tracked_species=[lynx],         # las que Trapper vigila
        sex=True,
        age=True,
    )
)
print(classificator.pk, classificator.name)
```

`create()` recibe un `ClassificatorCreate`, un modelo de Pydantic, y devuelve el clasificador creado.
Construir el modelo valida los datos antes de enviar nada. Para construirlo desde un diccionario usa
`ClassificatorCreate.model_validate(datos)`.

| Campo | Significado | Por defecto |
|---|---|---|
| `name` | hasta 255 caracteres, único | obligatorio |
| `template` | `ClassificatorTemplate.INLINE` (`"inline"`) o `TAB` (`"tab"`, en pestañas): cómo se dispone el formulario de clasificación | `INLINE` |
| `species` | las especies entre las que se puede elegir, como objetos de [`client.species`](species.md) o claves primarias. Vacío significa **todas las especies** | vacío |
| `tracked_species` | las especies que Trapper **vigila** (objetos o claves primarias): al clasificar una, se avisa a los administradores del proyecto (un correo y un mensaje). Deben estar entre las `species` cuando esa lista no está vacía | vacío |
| `sex`, `age`, `count_new`, `behaviour`, `individual_id`, `classification_confidence` | añade ese atributo opcional al formulario de clasificación | `False` |

El tipo de observación, el recuento y «es de montaje» (`is_setup`) forman siempre parte del formulario,
así que no son parámetros.

!!! note "`species` y `tracked_species` son listas distintas"
    `species` es lo que quien clasifica *puede elegir*. `tracked_species` es un subconjunto de esas
    especies que Trapper *vigila*: la misma especie puede estar en las dos, pero solo la segunda genera
    un aviso.

!!! warning "Las especies desconocidas se descartan en silencio"
    Trapper ignora una clave de especie que no existe: si todas las de `species` son desconocidas, el
    clasificador se crea aceptando todas las especies. Comprueba las claves con
    [`client.species`](species.md) cuando importe.

Los atributos personalizados y predefinidos (los campos extra que un clasificador puede añadir al
formulario) **no** están cubiertos. Un formulario rechazado lanza `APIError` indicando el campo, por
ejemplo `name: Classificator with this Name already exists.`; con `raise_on_error=False` devuelve `None`.
