# Versiones de Trapper (v1 y v2)

El SDK funciona tanto con Trapper v1 como con Trapper v2 (`2.0.0a2` en el momento de escribir esto).

```python
client = TrapperClient(access_token="...", base_url="https://trapper.example.org")
client.server_version          # "v1" o "v2": se detecta una vez y se guarda en caché
client.server_release          # versión exacta, p. ej. "2.0.0a" (None si el servidor no la indica)
```

## Detección de la versión

Con `trapper_version="auto"` (el valor por defecto) el cliente lee el endpoint público
`GET api/cs/version/` y toma el número mayor de la versión que informa:

| Versión informada | Versión |
|---|---|
| `v1.7.4-2-g7540e9ed` | v1 |
| `2.0.0a` | v2 |

La cadena exacta está disponible en `client.server_release`.

Si ese endpoint no da una respuesta utilizable (una compilación antigua, o un token no válido: DRF
responde `401` incluso en rutas públicas), el cliente recurre a `GET storage/api/upload-auth/`, una
ruta que solo existe en v2:

| Respuesta | Significado |
|---|---|
| `404` | v1 |
| `200`, `401`, `403` | v2 (la ruta existe, valga lo que valga el token) |
| cualquier otra | no concluyente → `APIError`; indica tú la versión |

Para evitar la sonda, pasa `trapper_version="v1"` o `"v2"`.

## La nueva API de Trapper 2 (`ninja`)

Trapper 2 está estrenando una API nueva bajo `/api/v2/...` (rama `refactor-api-ninja`, release `2.0.0a4`), con un
esquema versionado y documentado. Mientras se construye, el servidor sirve las dos: las rutas antiguas y las nuevas.
El SDK usa la nueva cuando está disponible:

```python
client = TrapperClient(access_token="...", base_url="https://trapper.example.org")
client.server_version   # "v2": es Trapper 2.x
client.api_flavor       # "ninja" si el servidor sirve la API nueva; si no, "legacy"
```

Con `trapper_version="auto"`, un servidor v2 que responde a `GET api/v2/probe/auth/` (`200` o `401`; v1 y la primera
v2 responden `404`) usa la API nueva. `trapper_version="ninja"` la fuerza, y `trapper_version="v2"` mantiene las
rutas antiguas.

En la API nueva:

- Las listas usan sus rutas: localizaciones, despliegues, recursos (también por colección y por localización),
  colecciones, proyectos de investigación y sus colecciones, proyectos de clasificación y sus colecciones,
  clasificadores, clasificaciones finales, de usuario y de IA, el mapa de clasificaciones, secuencias, especies y
  usuarios. Las tablas, exportaciones e importaciones siguen yendo de momento por las rutas antiguas.
- Las listas se ordenan por `pk` (`sort_by=pk`) salvo que pases `sort_by`: sus páginas nunca repiten ni se saltan
  filas. Se aceptan `sort_by`, `reverse` y `all_filtered`.
- `deployment` y `collection` de las listas de clasificaciones funcionan sin `project`.
- Las colecciones de un proyecto de investigación que el usuario no puede ver responden `403` (la ruta antigua
  respondía con una lista vacía).

## Qué cambia

| Funcionalidad | v1 | v2 |
|---|---|---|
| Subida de paquetes | `HTTPUploader` (protocolo propio por fragmentos) | `TusUploader` (tus 1.0 / tusd) |
| `client.upload_auth()` | — | ✔ |
| `client.maps`, `client.locations_geojson` | ✔ | `UnsupportedVersionError` (usa `deployments.geojson()`) |
| `deployments.geojson()` | `UnsupportedVersionError` | ✔ (`api/deployments/geojson/`) |
| `collections.*_ondemand` | ✔ | `UnsupportedVersionError` |
| `locations.import_locations`, `deployments.import_deployments` | ✔ (formulario web de importación) | ✔ (acción de importación del admin de Django; requiere una cuenta staff y se ejecuta de forma asíncrona) |
| `classification_results.import_classifications(overwrite_attrs=True)` | ✔ | `UnsupportedVersionError` (v2 eliminó la opción) |
| `client.project_deployments` | `UnsupportedVersionError` | ✔ |
| `research_projects.create()` | ✔ (formulario web) | `UnsupportedVersionError` |
| `classification_projects.create()`, `.add_collections()`, `.remove_collection()` | ✔ (formularios web) | `UnsupportedVersionError` |
| `classificators.create()` | ✔ (formulario web) | `UnsupportedVersionError` |
| Todo lo demás | ✔ | ✔ |

## Subir ficheros

```python
uploader = client.get_uploader()          # HTTPUploader en v1, TusUploader en v2
uploader.upload(Path("/data/package.zip"), "season1/package.zip")
```

En v2 el cargador se autentica con `Authorization: Token ...`, así que el cliente necesita un
`access_token`. Llama primero a `client.upload_auth()` para saber, antes de mover ningún byte, si el
token puede subir ficheros (`403` = no tiene cuenta de cargador). Una subida interrumpida se reanuda
desde el último byte que conserva el servidor; su URL se guarda en un fichero auxiliar
`<fichero>.tusmeta.json`.

### Cuenta de cargador (v2)

Un token válido no basta para subir ficheros en v2: el usuario necesita además una **cuenta de cargador
HTTP** (`UserHttpUploaderAccount`), que un administrador de Trapper concede en el admin de Django
(*Accounts → User HTTP uploader accounts → Add*, eligiendo al usuario). Sin ella, el servidor rechaza
la subida con `403 "HTTP uploader access not granted"`.

```python
try:
    client.upload_auth()                    # {"username": "..."} cuando el token puede subir
except err.ForbiddenError:
    ...                                     # token válido, pero aún sin cuenta de cargador
except err.UnauthorizedError:
    ...                                     # token desconocido o ausente
```

Compruébalo una vez antes de una subida larga en lugar de descubrirlo en el primer byte. v1 no tiene
ese requisito (ni `upload_auth()`: lanza `UnsupportedVersionError`).
