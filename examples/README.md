# Ejemplos

Scripts pequeños y ejecutables que muestran cómo usar `trapper_client` para tareas concretas.

## get_user_research_projects.py

Lista los research projects de un usuario, autenticándose como ese usuario y filtrando
por `owner=True` (el filtro `owner` de Trapper es booleano y siempre se resuelve contra
el usuario autenticado en la petición — no existe un filtro `owner=<user_id>`).

```bash
export WILDINTEL_BASE_URL="https://tu-servidor-trapper.example"
export WILDINTEL_ACCESS_TOKEN="<token del usuario>"
# o, en vez de un token:
#   export WILDINTEL_USER_NAME="..."
#   export WILDINTEL_USER_PASSWORD="..."

uv run python examples/get_user_research_projects.py
```

## get_classification_projects_for_research_project.py

Lista los proyectos de clasificación (classification projects) vinculados a un research
project dado, filtrando `/media_classification/api/projects` por `research_project=<pk>`
(cada classification project pertenece a exactamente un research project).

```bash
export WILDINTEL_BASE_URL="https://tu-servidor-trapper.example"
export WILDINTEL_ACCESS_TOKEN="<token>"
# o, en vez de un token:
#   export WILDINTEL_USER_NAME="..."
#   export WILDINTEL_USER_PASSWORD="..."

uv run python examples/get_classification_projects_for_research_project.py <research_project_pk>
```

## download_camtrapdp_for_classification_project.py

Genera (o reutiliza de caché) el paquete Camtrap DP de un proyecto de clasificación y lo
descarga a disco. `/media_classification/api/package/{pk}/` devuelve una URL de descarga
ya absoluta y con su propio token de un solo uso (`?rt=...`) — el script la descarga tal
cual con `client.make_request()`, sin volver a anteponerle `base_url`.

```bash
export WILDINTEL_BASE_URL="https://tu-servidor-trapper.example"
export WILDINTEL_ACCESS_TOKEN="<token>"
# o, en vez de un token:
#   export WILDINTEL_USER_NAME="..."
#   export WILDINTEL_USER_PASSWORD="..."

uv run python examples/download_camtrapdp_for_classification_project.py <classification_project_pk> [salida.zip]
```

## get_user_locations.py

Lista las localizaciones (`/geomap/api/locations`) de un usuario dado, ya sea por su pk o
por su username. A diferencia de `owner` en research/classification projects (booleano,
atado siempre al usuario autenticado), locations soporta `owners=<pk>` — un filtro por pk
arbitrario, así que **no hace falta autenticarse como ese usuario**, solo tener visibilidad
sobre sus localizaciones. Si se pasa un username, se resuelve a pk recorriendo
`/accounts/api/users` en el cliente (ese endpoint no tiene filtro de búsqueda en servidor).

```bash
export WILDINTEL_BASE_URL="https://tu-servidor-trapper.example"
export WILDINTEL_ACCESS_TOKEN="<token>"
# o, en vez de un token:
#   export WILDINTEL_USER_NAME="..."
#   export WILDINTEL_USER_PASSWORD="..."

uv run python examples/get_user_locations.py <user_pk_o_username>
```

## get_location_deployments.py

Lista los deployments (`/geomap/api/deployments`) de una localización dada, filtrando por
`location=<pk>` — igual que `owners` en locations, es un filtro por pk arbitrario, así que
no hace falta ser el owner de la localización para consultar sus deployments.

```bash
export WILDINTEL_BASE_URL="https://tu-servidor-trapper.example"
export WILDINTEL_ACCESS_TOKEN="<token>"
# o, en vez de un token:
#   export WILDINTEL_USER_NAME="..."
#   export WILDINTEL_USER_PASSWORD="..."

uv run python examples/get_location_deployments.py <location_pk>
```

## import_locations.py

Importa localizaciones desde un CSV. `/geomap/api/locations` es de solo lectura —
no hay endpoint REST para crear locations — así que usa
`client.locations.import_locations()`, que simula el formulario clásico
`geomap/location/import/` de la web (auth por cookie/sesión, no por token). Por eso
este script necesita **usuario + contraseña** (`WILDINTEL_USER_NAME` debe ser el
**email** de la cuenta) — un `WILDINTEL_ACCESS_TOKEN` no basta aquí, a diferencia
del resto de ejemplos. Es un workaround sobre una vista HTML sin versionar, no una
integración estable (ver el aviso en el docstring de `import_locations`).

Incluye un CSV de ejemplo ya válido, `sample_locations.csv` (columnas requeridas por el
`LocationImporter` del servidor: `locationID`, `longitude`, `latitude`, más las opcionales
`locationName` y `coordinateUncertainty`).

`research_project_pk` y `timezone` son obligatorios. El form del servidor declara ambos campos
`required=False`, pero:
- `clean_research_project()` rechaza un valor vacío en la práctica — si no lo pasas, el servidor
  responde con un `200` (el formulario re-renderizado con el error), no con un fallo claro.
- `timezone` es peor: nada lo rechaza en el momento del import. El servidor guarda las locations
  con `bulk_create()`, que **se salta la validación normal del modelo** — así que un timezone
  vacío crea locations con ese campo corrupto sin avisar. El fallo no aparece hasta *después*,
  cuando algo lista o filtra esas locations (esta API, o la propia interfaz web) y el serializer
  revienta con la timezone inválida — típicamente un `500` en una petición que a priori no tiene
  nada que ver, mucho después de que el import ya hubiera "funcionado".

```bash
export WILDINTEL_BASE_URL="https://tu-servidor-trapper.example"
export WILDINTEL_USER_NAME="tucuenta@example.com"   # tiene que ser el email de la cuenta
export WILDINTEL_USER_PASSWORD="..."

uv run python examples/import_locations.py examples/sample_locations.csv <research_project_pk> <timezone>
```

Para CSVs muy grandes, `--split` los trocea en varios ficheros CSV autocontenidos de ≤512 KB
(no hay protocolo de subida troceada real en este endpoint) y los importa uno a uno, con
`--delay SECONDS` de espera entre cada subida (por defecto 1 segundo):

```bash
uv run python examples/import_locations.py examples/sample_locations.csv <research_project_pk> <timezone> --split --delay 2
```

## import_deployments.py

Importa deployments desde un CSV, con el mismo mecanismo (y la misma limitación de
credenciales) que `import_locations.py`, simulando `geomap/deployment/import/`.
A diferencia de locations, aquí `timezone` es obligatorio (el form del servidor no
tiene valor por defecto), y `research_project_pk` también es obligatorio (mismo motivo
que en locations: el campo es `required=False` pero `clean_research_project()` lo exige
en la práctica). Usa `--create-locations` si el CSV también trae columnas
`locationID`/`longitude`/`latitude` para crear locations nuevas, o `--update` para
actualizar deployments existentes (requiere columna `_id` en el CSV).

Incluye un CSV de ejemplo ya válido, `sample_deployments.csv` (columnas requeridas por el
`DeploymentImporter` del servidor cuando se usa `--create-locations`: `deploymentID`,
`locationID`, `longitude`, `latitude`, `deploymentStart`, `deploymentEnd`, más la opcional
`cameraModel`):

```bash
export WILDINTEL_BASE_URL="https://tu-servidor-trapper.example"
export WILDINTEL_USER_NAME="tucuenta@example.com"   # tiene que ser el email de la cuenta
export WILDINTEL_USER_PASSWORD="..."

uv run python examples/import_deployments.py examples/sample_deployments.csv Europe/Madrid <research_project_pk> --create-locations
```

Igual que en `import_locations.py`, admite `--split --delay SECONDS` para CSVs muy grandes. Cuidado
al combinarlo con `--create-locations`: cada chunk es una petición independiente, así que si un
mismo `locationID` aparece en más de un chunk, el servidor intenta crear esa location otra vez en
cada chunk que la referencia (no sabe nada de lo creado en chunks anteriores).

Si en cambio quieres usar deployments ligados a locations ya existentes (sin `--create-locations`),
quita las columnas `longitude`/`latitude` del CSV y asegúrate de que los `locationID` referenciados
ya existan en el research project de destino — si no, el servidor rechaza el import con un mensaje
pidiendo activar `--create-locations`.

## import_classifications.py

Importa observaciones (especie, count, aprobación, ...) en un proyecto de clasificación, usando
`client.classification_results.import_classifications()` — a diferencia de los dos anteriores, este
sí es un endpoint REST real con auth por token (`WILDINTEL_ACCESS_TOKEN` funciona aquí, no hace
falta usuario/contraseña).

**Importante — este import es distinto en naturaleza**: no crea observaciones nuevas, **actualiza
clasificaciones que ya existen** en el proyecto, identificadas por su `_id` interno (la primary key
de esa clasificación en Trapper). El servidor rechaza cualquier `_id` que no exista ya en ese
proyecto. Por eso el CSV de ejemplo estático (`sample_observations.csv`, con `_id` 1 y 2) es solo
una plantilla — casi seguro que esos IDs no existen en tu proyecto real.

El script tiene un modo `--fetch` para generar un CSV con datos **reales** de tu propio proyecto
(de solo lectura, 100% seguro), que luego sí puedes reimportar tal cual como prueba, o editar antes
(p. ej. cambiar una especie) para comprobar que el import realmente aplica el cambio:

```bash
export WILDINTEL_BASE_URL="https://tu-servidor-trapper.example"
export WILDINTEL_ACCESS_TOKEN="<token>"
# o, en vez de un token:
#   export WILDINTEL_USER_NAME="..."
#   export WILDINTEL_USER_PASSWORD="..."

# Paso 1: obtener un CSV real e importable con 5 observaciones de tu proyecto
uv run python examples/import_classifications.py <project_id> real_observations.csv --fetch 5

# Paso 2: reimportarlo (opcionalmente edita un valor antes para ver que se aplica)
uv run python examples/import_classifications.py <project_id> real_observations.csv
```

Igual que en `import_locations.py`/`import_deployments.py`, admite `--split --delay SECONDS` para
trocear CSVs muy grandes en varios ficheros de ≤512 KB, subidos uno a uno con una pausa entre ellos:

```bash
uv run python examples/import_classifications.py <project_id> huge_observations.csv --split --delay 2
```

A diferencia de locations/deployments, este es un endpoint REST real pensado para recibir el
fichero completo en una sola petición — usa `--split` solo si un CSV muy grande da problemas de
tamaño de request o timeout. Con `--split`, el resultado se imprime por chunk (`[chunk N/M] ...`).
