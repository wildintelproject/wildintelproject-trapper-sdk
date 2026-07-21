# wildintel-trapper-sdk

![WildINTEL](img/wildIntel_logo.webp){ style="display: block; margin: 0 auto;" }

**wildintel-trapper-sdk** is a typed Python client for the REST API of
[Trapper](https://gitlab.com/trapper-project/trapper), the open-source platform used to manage and
classify camera-trap data: locations, deployments, media resources, storage collections, research
projects, and both manual and AI-assisted classification results.

Every Trapper resource is exposed as a typed Python component sharing the same interface for
pagination, filtering, and export — plus write access for the two resources (locations,
deployments) the REST API doesn't expose natively.

---

## Documentation Map

**[Installation](installation.md)**

Installing the package with pip/uv, or setting up the repository for development.

**[Usage](usage.md)**

The six access patterns shared by every component (`get`, `get_all`/`all`, `where`, `find`,
`export`), and the intermediate-table pk gotcha worth knowing about up front.

**Component Guides**

One guide per resource — Locations, Deployments, Classifications, Classification Projects,
Resources, Collections, and more — see the sidebar for the full list.

**[Features](features.md)**

What the client covers in detail: reading data, typed models, the write-access workarounds for
locations/deployments, chunked uploads and retries, authentication, and error handling.

**[Testing](testing.md)**

The three test layers (`unit`, `integration`, `e2e`) and how to run each.

**[API Reference](api/index.md)**

Full generated reference for every component, schema, and the low-level client.

**[About](about.md)**

Project background and WildINTEL funding.

---

## Installation

<div class="termy">

```console
$ pip install wildintel-trapper-sdk
---> 100%
Successfully installed wildintel-trapper-sdk

// Or, with uv:
$ uv add wildintel-trapper-sdk
Resolved 1 package in 340ms
Installed 1 package in 12ms
 + wildintel-trapper-sdk==0.1.0
```

</div>

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
