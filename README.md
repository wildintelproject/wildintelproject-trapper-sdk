# trapper_api_client

Cliente Python para la API de Trapper.

## Instalacion con uv

```bash
cd /home/ijfviana/Documentos/Programacion/trapper-project/trapper_api_client
uv sync --group dev
```

## Uso rapido

```python
from trapper_api_client.trapper_client import TrapperClient

client = TrapperClient(
    access_token="<token>",
    base_url="https://tu-trapper.example",
)

page = client.locations.get(page=1, page_size=10)
print(page.pagination)
```

## Tests

```bash
cd /home/ijfviana/Documentos/Programacion/trapper-project/trapper_api_client
uv run pytest tests -m "unit or integration" -q
```

## Documentacion (MkDocs)

```bash
cd /home/ijfviana/Documentos/Programacion/trapper-project/trapper_api_client
uv run mkdocs serve
```

