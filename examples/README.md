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
