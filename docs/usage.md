# Uso

```python
from trapper_api_client.trapper_client import TrapperClient

client = TrapperClient(
    access_token="<token>",
    base_url="https://tu-trapper.example",
)

# Una pagina de localizaciones
page = client.locations.get(page=1, page_size=20)
print(page.pagination)

# Descarga media de clasificacion en paralelo
files = client.classification_media.download_project_media_files(
    project_pk=7,
    output_dir="/tmp/media",
    parallel=True,
    max_workers=8,
    compress=True,
)
print(len(files))
```

