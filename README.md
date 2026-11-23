# <img src="docs/img/wildIntel_logo_cropped.webp" alt="WildINTEL logo" height="40" align="absmiddle"> <img src="docs/img/logo.png" alt="wildintel-trapper-sdk logo" height="40" align="absmiddle"> wildintel-trapper-sdk

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-GPLv3-blue.svg)
[![WildINTEL](https://img.shields.io/badge/WildINTEL-v1.0-blue)](https://wildintel.eu/)
[![TRAPPER](https://img.shields.io/badge/TRAPPER-Server-green)](https://gitlab.com/trapper-project/trapper)

<hr>

## Typed Python client for the Trapper API

**wildintel-trapper-sdk** is an open-source Python client for the REST API of
[TRAPPER](https://gitlab.com/trapper-project/trapper), the platform the [WildINTEL](https://wildintel.eu/) project
uses to manage and classify camera-trap data. Every resource — locations, deployments, media resources, storage
collections, research projects, classification projects and their results — is a typed component with the same
interface for pagination, filtering and CSV export. It works with **Trapper v1 and Trapper v2**: the version of the
server is detected on first use.

Where Trapper's REST API is read-only, the SDK also **writes**: it imports locations, deployments and classifications,
creates research projects, classification projects (with their members) and classificators, and uploads data
packages — resumable on Trapper v2. It is the layer that the other tools of the WildINTEL toolchain, such as
[wildintel-uploader](https://github.com/wildintelproject/wildintel-uploader) and
[wildintel-publisher](https://github.com/wildintelproject/wildintel-publisher), use to talk to a Trapper server.

## 🚀 Quick start

```bash
pip install wildintel-trapper-sdk
# or: uv add wildintel-trapper-sdk
```

Uploading packages to a Trapper v1 server needs the `upload` extra: `pip install "wildintel-trapper-sdk[upload]"`.

```python
from trapper_client import TrapperClient

client = TrapperClient(
    base_url="https://your-trapper.example",
    access_token="<token>",
)
print(client.server_version)        # "v1" or "v2", detected from the server

# Iterate over all locations
for loc in client.locations.where(page_size=50):
    print(loc.pk, loc.name)

# Fetch one page of deployments
page = client.deployments.get(page=1, page_size=25)
print(page.pagination.count, "deployments found")

# Export classification results to CSV
client.classification_results.export_project_results(project_pk=7, file="results.csv")
```

The operations that Trapper only offers as web forms (imports, and the creation of projects and classificators)
log in with `user_name` and `user_password` — the account's *email* on servers that log in by email — instead of a
token. See the [Usage guide](https://wildintelproject.github.io/wildintelproject-trapper-sdk/usage/) for the full
set of access patterns, and the guide of each component for its filters and write operations.

To work on the SDK itself:

```bash
git clone https://github.com/wildintelproject/wildintelproject-trapper-sdk.git
cd wildintelproject-trapper-sdk
./setup.sh
```

## ✨ Features

**Reading data**

- **One component per resource** — each endpoint has its own class with the same six methods: `get` (one page), `get_all` (every page merged), `where` and `all` (lazy iteration), `find` (by primary key) and `export` (to CSV, or to a list of models)
- **Transparent pagination and filtering** — `where()` fetches the pages as you iterate it; the filters of each endpoint are plain keyword arguments
- **Fully typed** — Pydantic v2 models for every response, with full autocompletion in any IDE; endpoints that can answer in the CamtrapDP or in Trapper's own shape are resolved automatically

**Writing where the REST API falls short**

- Import **locations and deployments** from CSV, with `wait_for_import()` to wait for Trapper to process them, and **classifications** through Trapper's own endpoint, with the table checked locally first
- **Create research projects, classification projects and classificators**, with the members and roles of the projects, and link the collections of a classification project — from validated input models and typed enumerations (Trapper v1)
- Large CSVs can be **split** into chunks, and network failures are retried with exponential backoff

**Uploading data**

- `client.get_uploader()` returns the right uploader for the server: a **chunked HTTP** one on Trapper v1, and a **resumable tus** one on v2, which carries on from the last byte after an interruption

**Trapper v1 and v2**

- The version is detected automatically (or set with `trapper_version`); what v2 removed raises `UnsupportedVersionError`, and what only v2 has — the deployments of a classification project, deployments as GeoJSON — is documented as such

**General**

- Authentication with a static **token**, or with **username and password**
- Mapped **exceptions** that carry the server's own message and, for rejected forms, the field that failed
- **Documentation in English and Spanish**, with a compatibility note on every guide

## 📋 Requirements

**To run it**

- Python 3.10+ with [uv](https://docs.astral.sh/uv/) (or pip)
- Access to a running [TRAPPER](https://gitlab.com/trapper-project/trapper) server, v1 or v2, and an account on it. The web-form operations need the account's user name and password, and uploading on v2 needs an *HTTP uploader account* that a Trapper administrator grants
- The `upload` extra — [aiofiles](https://github.com/Tinche/aiofiles) and [BLAKE3](https://github.com/oconnor663/blake3-py) — only to upload packages to a Trapper v1 server

**Technology stack**

| Layer | Technologies |
|---|---|
| HTTP | [HTTPX](https://www.python-httpx.org/), [tenacity](https://tenacity.readthedocs.io/) (retries), [attrs](https://www.attrs.org/) |
| Models | [Pydantic](https://docs.pydantic.dev/) 2 |
| Uploads | tus 1.0 (resumable, Trapper v2) and a chunked protocol with BLAKE3 checksums (Trapper v1) |
| Testing | [pytest](https://pytest.org/), pytest-mock, [responses](https://github.com/getsentry/responses) |
| Docs and tooling | [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) with mkdocstrings and mkdocs-static-i18n, [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/) (development CLI), GitHub Actions |

## 📚 Documentation

Full documentation, in English and Spanish, is available at **https://wildintelproject.github.io/wildintelproject-trapper-sdk/**

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

To report a bug or request a new feature, please open an [issue](https://github.com/wildintelproject/wildintelproject-trapper-sdk/issues).

## 🏛️ Funding

This work is part of the [WildINTEL project](https://wildintel.eu/), funded by the [Biodiversa+](https://www.biodiversa.eu/) Joint Research Call 2022-2023 "Improved
transnational monitoring of biodiversity and ecosystem change for science and society (BiodivMon)". Biodiversa+ is the
European co-funded biodiversity partnership supporting excellent research on biodiversity with an impact for policy and
society. Biodiversa+ is part of the European Biodiversity Strategy for 2030 that aims to put Europe's biodiversity on a
path to recovery by 2030 and is co-funded by the European Commission.

WildINTEL has been co-funded by the [European Commission](https://commission.europa.eu/) (GA No. 101052342) and the following funding organisations: [Agencia Estatal de Investigación](https://www.aei.gob.es/) (Spain, PCI2023-145963-2, PCI2024-153489), [National Science Centre](https://www.ncn.gov.pl/?language=en) (Poland, UMO-2023/05/Y/NZ8/00104), the [Research Council of Norway](https://www.forskningsradet.no/en/) (Norway, NFR350962) and the [German Research Foundation](https://www.dfg.de/en/) (Germany).

## 📝 License

This project is licensed under the GNU General Public License v3.0 or later - see the [LICENSE](LICENSE) file for details.

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
