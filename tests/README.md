# trapper_api_client Tests

Suite de pruebas para `trapper_client` con tres niveles:

- **unit**: lógica aislada sin red.
- **e2e**: pruebas contra servidor real (opt-in).

## Requisitos

Instala dependencias de desarrollo desde `pyproject.toml`.

## Ejecutar tests locales (unit + integration)

```bash
cd /home/ijfviana/Documentos/Programacion/trapper-project/trapper_api_client
uv sync --group dev
uv run pytest tests -m "unit or integration" -q
```

## Ejecutar smoke tests contra servidor real

Variables soportadas:

- `WILDINTEL_SMOKE_ENABLED=1` (obligatoria para habilitar smoke)
- `WILDINTEL_BASE_URL` (obligatoria)
- `WILDINTEL_ACCESS_TOKEN` **o** `WILDINTEL_USER_NAME` + `WILDINTEL_USER_PASSWORD`
- `WILDINTEL_VERIFY_SSL` (`1|0`, opcional, por defecto `1`)
- `WILDINTEL_TIMEOUT` (opcional, por defecto `30`)
- `WILDINTEL_PROJECT_PK` (opcional, habilita smoke de media de clasificación)

Ejemplo:

```bash
cd /home/ijfviana/Documentos/Programacion/trapper-project/trapper_api_client
export WILDINTEL_SMOKE_ENABLED=1
export WILDINTEL_BASE_URL="https://tu-trapper.example"
export WILDINTEL_ACCESS_TOKEN="<token>"
export WILDINTEL_PROJECT_PK="7"
uv run pytest -m e2e tests/test_real_server_smoke.py -q
```

## Nota

Los smoke tests no hacen operaciones destructivas; solo lecturas.

## GitHub Actions

Se incluye el workflow `.github/workflows/tests.yml` con:

- job automático `unit-integration` en `push` y `pull_request`
- job `smoke` manual via `workflow_dispatch` (solo si activas `run_smoke=true`)

### Secrets recomendados en GitHub

- `WILDINTEL_BASE_URL`
- `WILDINTEL_ACCESS_TOKEN` **o** `WILDINTEL_USER_NAME` + `WILDINTEL_USER_PASSWORD`
- `WILDINTEL_VERIFY_SSL` (opcional)
- `WILDINTEL_TIMEOUT` (opcional)

