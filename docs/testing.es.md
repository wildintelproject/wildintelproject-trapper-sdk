# Pruebas

La batería de pruebas se divide en tres capas:

| Marcador | Descripción | ¿Requiere un servidor? |
|--------|-------------|-------------------|
| `unit` | Pruebas unitarias puras: todas las llamadas HTTP están simuladas | No |
| `integration` | Pruebas de componentes con respuestas HTTP simuladas | No |
| `e2e` | Pruebas de humo contra una instancia real de Trapper | Sí |

El repositorio incluye además un pequeño `cli.py` que envuelve `pytest` con estos marcadores, para que
no tengas que recordar las opciones `-m`/`-k`:

<div class="termy">

```console
$ uv run cli test unit
╭──────────── wildintel-trapper-sdk — tests ────────────╮
│ Suite: unit   Marcador: -m "unit"                      │
╰─────────────────────────────────────────────────────────╯
................................................... [100%]
1100 passed in 2.10s
```

</div>

## Ejecutar las pruebas unitarias y de integración

<div class="termy">

```console
$ uv run cli test all
// Equivale a:
$ uv run pytest tests -m "unit or integration" -q
```

</div>

## Ejecutar solo las pruebas unitarias

<div class="termy">

```console
$ uv run cli test unit
// Equivale a:
$ uv run pytest tests/unit -q
```

</div>

## Ejecutar las pruebas de extremo a extremo

Las pruebas E2E usan un servidor Trapper real, que puede ser v1 o v2. Define estas variables de entorno
antes de ejecutarlas:

```bash
export WILDINTEL_SMOKE_ENABLED=1
export WILDINTEL_BASE_URL="https://your-trapper.example"
export WILDINTEL_ACCESS_TOKEN="<token>"        # o usa usuario/contraseña más abajo
export WILDINTEL_USER_NAME="user"
export WILDINTEL_USER_PASSWORD="password"
export WILDINTEL_VERIFY_SSL=1                  # 0 para omitir la verificación SSL
export WILDINTEL_TIMEOUT=30
```

Después ejecuta:

<div class="termy">

```console
$ uv run cli test e2e
// Equivale a:
$ uv run pytest tests/e2e -m e2e -q
```

</div>

También puedes copiar `tests/env.example` a `tests/.env` y rellenar los valores: pytest lo cargará
automáticamente.

## Desplegar Trapper v1 y v2 para probar

`uv run cli trapper` despliega con Docker Compose un Trapper v1 y un Trapper v2, siempre con las mismas cuentas, para que
las pruebas de extremo a extremo tengan contra qué ejecutarse. Necesita Docker y (la primera vez) red hacia el registro.
**No** despliega Trapper AI ni el frontend de ciencia ciudadana: son otros contenedores.

<div class="termy">

```console
$ uv run cli trapper up                            // v1 y v2 (v1: latest, v2: 2.0.0a2)
$ uv run cli trapper up v2 --branch development     // otra rama de Trapper
$ uv run cli trapper up --port-offset 1000          // otra instancia: puertos + 1000, con sus propios contenedores y datos
$ eval "$(uv run cli trapper env v2)"               // WILDINTEL_* para los tests e2e
$ uv run cli test e2e
$ uv run cli trapper status | logs v2 trapper-celery | down | destroy
```

</div>

- **La rama** es la etiqueta de la imagen `registry.gitlab.com/trapper-project/trapper:<rama>`: el nombre tal como lo das
  (`2.0.0a2`, `latest`) o el que el CI de Trapper da a una rama (`refactor/api-ninja` es `refactor-api-ninja`). El comando
  comprueba que la imagen existe. No construye Trapper desde el código.
- **Varias instancias**: `--port-offset N` suma `N` a todos los puertos y crea **otra instancia** (sus contenedores, volúmenes,
  subred y cuentas), que vive junto a las demás. Los otros comandos necesitan el mismo `--port-offset` para encontrarla
  (`uv run cli trapper env v2 --port-offset 1000`).
- **Puertos** (suma `--port-offset`): v1 en `8080` (nginx, el que hay que usar: sin él una descarga de fichero contesta
  `200` sin cuerpo), `8010` (la app) y `8088` (uploader); v2 en `8180`, `8100` y `8188`.
- **Cuentas** (contraseña `wildintel-sdk-test`; Trapper v1 entra con el correo, `<usuario>@example.org`): `sdktest`
  (superusuario, el del token de la API), `rp_staff` (staff y superusuario), `rp_user`, `ana`, `luis` y `plainuser`, cada
  una con su token, y el proyecto de investigación `SDKT` con `sdktest` y `rp_staff` como administradores, `ana` como
  experta y `luis` y `rp_user` como colaboradores. Ejecutar `up` otra vez las deja como están.
- `down` para la instancia y conserva sus datos; `destroy` borra también los datos. Los secretos y los tokens están en
  `dev/trapper/.state/`, que git no versiona.
- **Lo que una instancia aún no tiene**: localizaciones, deployments, imágenes y clasificaciones. Los tests que las
  necesitan se saltan o fallan en un servidor vacío (por ejemplo, una exportación de localizaciones contesta `400` si no
  hay ninguna, como hace Trapper).

## Filtrar por palabra clave u obtener una salida detallada

<div class="termy">

```console
$ uv run cli test unit -k import_locations -v
```

</div>

## Cobertura

<div class="termy">

```console
$ uv run pytest tests -m "unit or integration" --cov=src/trapper_client --cov-report=term-missing
```

</div>
