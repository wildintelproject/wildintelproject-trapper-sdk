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
