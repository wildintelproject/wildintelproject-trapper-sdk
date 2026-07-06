# <img src="img/wildIntel_logo.webp" alt="Wildintel Tools Logo" height="60">  trapper-client

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-GPLv3-blue.svg)
[![WildINTEL](https://img.shields.io/badge/WildINTEL-v1.0-blue)](https://wildintel.eu/)
[![Trapper](https://img.shields.io/badge/Trapper-Server-green)](https://gitlab.com/trapper-project/trapper)

<hr>

## Typed Python client for the Trapper API

## 🚀 Features

- **One component per resource** — each API endpoint has its own class with `get`, `get_all`, `where` (lazy iterator), `find`, and `export` methods.
- **Fully typed** — Pydantic v2 models for every response; full autocompletion in any IDE.
- **Transparent pagination** — `where()` fetches pages on demand; `get_all()` merges all pages into a single result.
- **CSV export** — any component can dump its data directly to a file with a single call.
- **Flexible authentication** — static token or username/password.
- **Robust retries** — `tenacity` handles transient network failures on every request.

## 📋 Requirements

* Python 3.10 or higher
* uv (for dependency management)
* Access to a running Trapper server instance

## 🧭 Overview

`trapper-client` is a Python library that wraps the REST API of [Trapper](https://gitlab.com/trapper-project/trapper),
the open-source platform for managing and classifying camera-trap data.

Every Trapper resource — locations, deployments, media resources, storage collections, research projects, classification
projects, and classification results — is exposed as a typed Python component. All components share the same interface:

| Method | Description |
|--------|-------------|
| `get(page, page_size, **filters)` | Fetch one page of results |
| `get_all(page_size, **filters)` | Fetch and merge all pages |
| `where(page_size, **filters)` | Lazy iterator; fetches pages on demand |
| `find(pk)` | Retrieve a single item by primary key |
| `export(file, **filters)` | Write all results to a CSV file |

```
trapper-client
├── TrapperClient                  ← high-level entry point
│   ├── client.locations           ← LocationsComponent
│   ├── client.locations_geojson   ← LocationsGeoJsonComponent
│   ├── client.deployments         ← DeploymentsComponent
│   ├── client.resources           ← ResourcesComponent
│   ├── client.collections         ← CollectionsComponent
│   ├── client.research_projects   ← ResearchProjectsComponent
│   ├── client.classification_projects         ← ClassificationProjectsComponent
│   ├── client.classifications                 ← ClassificationsComponent
│   ├── client.ai_classifications              ← AIClassificationsComponent
│   ├── client.classification_media            ← ClassificationMediaComponent
│   ├── client.classification_results_agg      ← ClassificationResultsAggComponent
│   └── client.classification_package          ← ClassificationPackageComponent
└── APIClientBase                  ← low-level HTTP helpers (get, post, patch, …)
```

## 💻 Installation

### Install with pip

```bash
pip install trapper-client
```

### Install with uv

```bash
uv add trapper-client
```

### Install for development

```bash
git clone https://github.com/trapper-project/trapper-client.git
cd trapper-client
setup.sh
```

## ⚡ Usage

### Creating a client

```python
from trapper_client import TrapperClient

# Token-based authentication
client = TrapperClient(
    base_url="https://your-trapper.example",
    access_token="<token>",
)

# Or username / password
client = TrapperClient(
    base_url="https://your-trapper.example",
    user_name="user",
    user_password="password",
)
```

### Fetching a single page

```python
page = client.locations.get(page=1, page_size=25)

print(page.pagination.count)   # total items on the server
for loc in page.results:
    print(loc.pk, loc.name)
```

Pass extra keyword arguments to filter results:

```python
page = client.deployments.get(page_size=50, research_project=3)
```

### Lazy iteration with `where()`

```python
for loc in client.locations.where(page_size=100):
    print(loc.pk, loc.name)
```

### Fetching all pages at once

```python
result = client.research_projects.get_all(page_size=100)
print(len(result.results), "projects")
```

### Finding a single item by PK

```python
loc = client.locations.find(42)
print(loc.name, loc.coordinates)
```

### Exporting to CSV

```python
path = client.locations.export(file="locations.csv")
print(f"Saved to {path}")
```

### Classification results

```python
# Paginated results for one project
page = client.classification_results.get_project_results(
    project_pk=7, page_size=50, approved=True,
)

# Export all results to CSV
client.classification_results.export_project_results(
    project_pk=7, file="observations.csv",
)

# Lazy iteration
for row in client.classification_results.where_project_results(project_pk=7):
    print(row.observationID, row.scientificName)
```

## 🧪 Testing

The test suite is split into three layers:

| Marker | Description | Requires a server? |
|--------|-------------|-------------------|
| `unit` | Pure unit tests — all HTTP calls are mocked | No |
| `integration` | Component tests with mocked HTTP responses | No |
| `e2e` | Smoke tests against a real Trapper instance | Yes |

```bash
# Unit and integration tests
uv run pytest tests -m "unit or integration" -q

# End-to-end tests (requires a live Trapper server)
export WILDINTEL_SMOKE_ENABLED=1
export WILDINTEL_BASE_URL="https://your-trapper.example"
export WILDINTEL_ACCESS_TOKEN="<token>"
uv run pytest tests/e2e -m e2e -q
```

## 📖 Documentation

```bash
uv run mkdocs serve   # live preview at http://127.0.0.1:8000
uv run mkdocs build   # static output in site/
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the GNU General Public License v3.0 or later - see the [LICENSE](LICENSE) file for details.

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License 
as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.


## 🏛️ Funding

This work is part of the [WildINTEL project](https://wildintel.eu/), funded by the Biodiversa+ Joint Research Call 2022-2023 "Improved
transnational monitoring of biodiversity and ecosystem change for science and society (BiodivMon)". Biodiversa+ is the 
European co-funded biodiversity partnership supporting excellent research on biodiversity with an impact for policy and
society. Biodiversa+ is part of the European Biodiversity Strategy for 2030 that aims to put Europe's biodiversity on a
path to recovery by 2030 and is co-funded by the European Commission. 
