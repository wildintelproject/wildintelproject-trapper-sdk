# <img src="img/wildIntel_logo.webp" alt="Wildintel Tools Logo" height="60">  wildintel-trapper-sdk

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-GPLv3-blue.svg)
[![WildINTEL](https://img.shields.io/badge/WildINTEL-v1.0-blue)](https://wildintel.eu/)
[![Trapper](https://img.shields.io/badge/Trapper-Server-green)](https://gitlab.com/trapper-project/trapper)

<hr>

## Typed Python client for the Trapper API

**wildintel-trapper-sdk** is a typed Python client for the REST API of
[Trapper](https://gitlab.com/trapper-project/trapper), the open-source platform used to manage and
classify camera-trap data. Every resource — locations, deployments, media resources, storage
collections, research projects, and classification results — is exposed as a Python component
sharing the same interface for pagination, filtering, and CSV export.

## ✨ Features

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

## 📚 Documentation

**https://wildintelproject.github.io/wildintel-trapper-sdk/**

## 🚀 Quick start

```bash
pip install wildintel-trapper-sdk
# or: uv add wildintel-trapper-sdk
```

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
    project_pk=7, file="results.csv",
)
```

See the [Usage guide](https://wildintelproject.github.io/wildintel-trapper-sdk/usage/) for the full
set of access patterns, and the per-component guides for filters and write-access details.

### Install for development

```bash
git clone https://github.com/wildintelproject/wildintel-trapper-sdk.git
cd wildintel-trapper-sdk
setup.sh
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
