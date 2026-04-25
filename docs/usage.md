# Usage

## Creating a client

Authenticate with a static token:

```python
from trapper_client import TrapperClient

client = TrapperClient(
    base_url="https://your-trapper.example",
    access_token="<token>",
)
```

Or with username and password:

```python
client = TrapperClient(
    base_url="https://your-trapper.example",
    user_name="user",
    user_password="password",
)
```

---

## Fetching a single page

Every component exposes `get()` for page-based access:

```python
page = client.locations.get(page=1, page_size=25)

print(page.pagination.count)   # total items on the server
print(page.pagination.pages)   # total number of pages
for loc in page.results:
    print(loc.pk, loc.name)
```

Pass extra keyword arguments to filter the results:

```python
page = client.deployments.get(page=1, page_size=50, research_project=3)
```

---

## Lazy iteration with `where()`

`where()` returns an [`APIQuery`](api/api_query.md) that fetches pages on demand.
Use it when you want to iterate over all items without loading them all into memory at once:

```python
for loc in client.locations.where(page_size=100):
    print(loc.pk, loc.name)
```

Apply a client-side filter:

```python
active = client.deployments.where(
    page_size=50,
    filter_fn=lambda d: d.end_date is None,
)
for dep in active:
    print(dep.pk)
```

Use it as a context manager to stop early:

```python
with client.locations.where(page_size=50) as query:
    first_ten = [next(query) for _ in range(10)]
```

---

## Fetching all pages at once

`get_all()` collects every page into a single `PaginatedResult`:

```python
result = client.research_projects.get_all(page_size=100)
print(len(result.results), "projects")
```

---

## Finding a single item by PK

```python
loc = client.locations.find(42)
print(loc.name, loc.coordinates)
```

---

## Exporting to CSV

`export()` writes all results to a CSV file and returns the path:

```python
path = client.locations.export(file="locations.csv")
print(f"Saved to {path}")
```

Pass `file=None` to get a list of model instances instead:

```python
records = client.deployments.export(file=None)
```

---

## Classification results

Fetch paginated results for a classification project:

```python
page = client.classification_results.get_project_results(
    project_pk=7,
    page=1,
    page_size=50,
    approved=True,
)
for row in page.results:
    print(row.observationID, row.scientificName)
```

Export all results for a project directly to CSV:

```python
client.classification_results.export_project_results(
    project_pk=7,
    file="observations.csv",
)
```

Iterate lazily:

```python
for row in client.classification_results.where_project_results(project_pk=7):
    print(row)
```

---

## Generic endpoint

For any endpoint not covered by a component, use `client.where()`:

```python
for item in client.where("api/deployments/", query={"colls": 7}):
    print(item)
```
