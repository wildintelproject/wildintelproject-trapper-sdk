# trapper_client

`trapper_client` is a typed Python client for the REST API of [Trapper](https://github.com/trapper-project/trapper), the open-source platform for managing and classifying camera-trap data.

---

## What is Trapper?

Trapper is a web application for handling large volumes of camera-trap data: locations, deployments, media resources, classification projects, and classification results — both manual and AI-assisted.

`trapper_client` exposes all those resources as Python components with a consistent interface for pagination, filtering, and export.

---

## Key features

- **One component per resource** — each endpoint has its own class with `get`, `get_all`, `where` (lazy iterator), `find`, and `export` methods.
- **Fully typed** — Pydantic v2 models for every response; full autocompletion in any IDE.
- **Transparent pagination** — `where()` fetches pages on demand; `get_all()` merges them into a single result.
- **CSV export** — any component can dump its data directly to a file.
- **Flexible authentication** — static token or username/password.
- **Robust retries** — `tenacity` handles network failures on every request.

---

## Installation

```bash
pip install trapper-client
# or with uv:
uv add trapper-client
```

---

## Quick start

```python
from trapper_client import TrapperClient

client = TrapperClient(
    base_url="https://your-trapper.example",
    access_token="<token>",
)

# Iterate over all locations
for loc in client.locations.where(page_size=50):
    print(loc.pk, loc.name)

# Fetch one page of deployments
page = client.deployments.get(page=1, page_size=25)
print(page.pagination.count, "deployments found")

# Export classification results to CSV
client.classification_results.export_project_results(
    project_pk=7,
    file="results.csv",
)
```

---

## Available resources

| Client attribute | API resource |
|---|---|
| `client.locations` | Locations |
| `client.locations_geojson` | Locations as GeoJSON |
| `client.deployments` | Deployments |
| `client.resources` | Media resources |
| `client.collections` | Storage collections |
| `client.research_projects` | Research projects |
| `client.classification_projects` | Classification projects |
| `client.classifications` | Classification observations |
| `client.ai_classifications` | AI-assisted classifications |
| `client.classification_media` | Classification media per project |
| `client.classification_results_agg` | Aggregated results per deployment |
| `client.classification_package` | Results data packages |
