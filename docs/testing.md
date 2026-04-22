# Testing

## Unit + integration

```bash
cd /home/ijfviana/Documentos/Programacion/trapper-project/trapper_api_client
uv run pytest tests -m "unit or integration" -q
```

## Smoke (servidor real)

```bash
cd /home/ijfviana/Documentos/Programacion/trapper-project/trapper_api_client
export WILDINTEL_SMOKE_ENABLED=1
export WILDINTEL_BASE_URL="https://tu-trapper.example"
export WILDINTEL_ACCESS_TOKEN="<token>"
uv run pytest tests/test_real_server_smoke.py -m e2e -q
```

