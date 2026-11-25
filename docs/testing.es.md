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

## Desplegar Trapper v1, v2 y v2-ninja, sembrar un dataset y lanzar los e2e

`uv run cli trapper` da a los tests end-to-end algo contra lo que ejecutarse: despliega Trapper con Docker Compose,
siempre con las mismas cuentas, lo siembra con un dataset de prueba y lanza `tests/e2e` con las variables que ese
dataset necesita. Requiere Docker y (la primera vez) red hasta el registro. **No** despliega Trapper AI ni el frontal de
ciencia ciudadana: son otros contenedores.

| Instancia | Imagen | nginx | API |
|---|---|---|---|
| `v1` | `trapper:latest` (1.7.4) | `8080` | la antigua (DRF) |
| `v2` | `trapper:2.0.0a2` | `8180` | la antigua (DRF) |
| `ninja` | `trapper:refactor-api-ninja` (2.0.0a4) | `8280` | la nueva (`/api/v2/`, Django Ninja), y la antigua |

<div class="termy">

```console
$ uv run cli trapper up                            // las tres (o: up v1 | up v2 | up ninja)
$ uv run cli trapper seed v2 --dataset 1           // o --dataset 2, o --dataset all
$ uv run cli trapper e2e v2 --dataset 1            // tests/e2e contra ella
$ uv run cli trapper e2e v2 --dataset 1 -- -k species -x    // tras --: opciones de pytest
$ eval "$(uv run cli trapper env v2 --dataset 1)"  // o las variables, para lanzar pytest a mano
$ uv run cli trapper status | logs v2 trapper-celery | down | destroy
```

</div>

- **Los datasets** (`dev/trapper/seed/dataset<N>.py`), sembrados con el SDK donde Trapper tiene una vía y con
  `manage.py shell` donde no. Sembrar otra vez no cambia nada.
    - **1, «Mamíferos de Doñana y Sierra Morena»**: pequeño y hecho a mano. 6 localizaciones, 7 deployments, 26 imágenes
      en dos colecciones de un proyecto de clasificación (de ciencia ciudadana en v2, slug `mamiferos-donana-sm`), 9
      especies, 22 clasificaciones aprobadas con sexo y edad, vacías y humanos, 4 pendientes (3 con clasificaciones de un
      experto y un colaborador que no coinciden), 2 clasificaciones de IA con cajas.
    - **2, «Cabañeros 2025»**: más de 500 filas en varias listas, para ver qué hace la paginación. 12 localizaciones, 14
      deployments, 640 imágenes en ráfagas de tres en dos colecciones y dos proyectos de clasificación, 12 especies, 600
      clasificaciones de usuario (55 pendientes) con vacías, humanos, vehículos, conteos y cajas; 66 filas de IA de dos
      proveedores.
- **Las variables de los e2e**: `env --dataset N` y `e2e --dataset N` leen las claves primarias de la instancia con el
  SDK (el proyecto y la colección del dataset, una localización con un recurso suyo, una clasificación de usuario...),
  para que los tests que las necesitan se ejecuten en vez de saltarse. Sin `--dataset`, `env` da solo la URL y las
  credenciales.
- **Un dataset por instancia** mantiene separados los resultados: se pueden sembrar los dos en una, pero algunos tests
  leen el servidor entero. Usa `--name` para otra instancia de la misma versión, con su propio `--port-offset`:
  `uv run cli trapper up v1 --name ds1 --port-offset 3000`, y las mismas opciones en `seed`, `env` y `e2e`.
- **La rama** (`--branch`, o `--v1-branch`, `--v2-branch`, `--ninja-branch`) es la etiqueta de la imagen
  `registry.gitlab.com/trapper-project/trapper:<rama>`: el nombre tal cual (`2.0.0a2`, `latest`) o el que el CI de
  Trapper da a una rama (`refactor/api-ninja` es `refactor-api-ninja`). El comando comprueba que la imagen exista. No
  compila Trapper desde el código.
- **Nombres**: cada instancia es el proyecto de compose `wildintel-sdktest-trapper-<nombre>` (`v1`, `v2`, `v2-ninja`,
  `v1-ds1`, `v2-p1000`...), así `docker ps` distingue las instancias de prueba. `--port-offset N` suma `N` a todos los
  puertos y, sin `--name`, llama a la instancia `<versión>-p<N>`.
- **Puertos** (suma `--port-offset`): usa nginx (sin él, una descarga de fichero responde `200` sin cuerpo); la app está
  en `8010`/`8100`/`8200` y el uploader en `8088`/`8188`/`8288` (v1/v2/ninja).
- **Cuentas** (contraseña `wildintel-sdk-test`; Trapper v1 entra con el e-mail, `<usuario>@example.org`): `sdktest`
  (superusuario, el del token de la API), `rp_staff` (staff y superusuario), `rp_user`, `ana`, `luis` y `plainuser`,
  cada una con su token (también para la API nueva), y el research project `SDKT` con `sdktest` y `rp_staff` como
  admins, `ana` como experta y `luis` y `rp_user` como colaboradores. Volver a ejecutar `up` las deja como están.
- `down` para la instancia y conserva sus datos; `destroy` borra también los datos. Los secretos, los tokens y lo
  sembrado están en `dev/trapper/.state/<nombre>/`, que git no versiona.
- **Memoria**: cada instancia ocupa unos 2–2,5 GB; para las que no uses.

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
