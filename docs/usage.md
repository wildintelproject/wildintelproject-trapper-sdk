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

Every resource is available as an attribute of `client` — `client.locations`, `client.deployments`,
`client.classification_results`, and so on (see the full list on the [Home](index.md#available-resources)
page). All of them share the exact same interface described below, because they all inherit it from
the same base class (`TrapperComponent`). Learning it once means you already know how to use every
component in the SDK.

---

## The six access patterns

Every component exposes the same six methods. They differ only in *how much* data they fetch and
*when*:

| Method | Returns | Use it when... |
|---|---|---|
| `get(page=1, page_size=50, **filters)` | One `PaginatedResult` page | You want a specific page — e.g. building your own pagination UI |
| `get_all(page_size=100, **filters)` | One `PaginatedResult` with *every* item merged | You want everything at once and it comfortably fits in memory |
| `where(**filters)` | Lazy `APIQuery` iterator | You want to stream through items page-by-page, without loading everything upfront |
| `all(**filters)` | Same as `where()` — it's a plain alias | You just want to read "iterate over all of this resource" |
| `find(pk)` | One typed model instance | You already know the primary key |
| `export(file=..., **filters)` | `Path` to a CSV file, or `list[Model]` if `file=None` | You want a CSV dump, or plain model instances without pagination bookkeeping |

Every `**filters` keyword becomes a query-string parameter sent to the server — which ones are
accepted depends on the component (see each component's page under **Component Guides** in the nav).

### `get()` — one page

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

### `get_all()` — every page, merged

`get_all()` calls `get()` repeatedly under the hood and merges every page into a single
`PaginatedResult`. Convenient, but it loads everything into memory before returning.

```python
result = client.research_projects.get_all(page_size=100)
print(len(result.results), "projects")
```

### `where()` and `all()` — lazy iteration

`where()` returns an [`APIQuery`](api/api_query.md): pages are fetched on demand as you iterate,
so memory use stays flat regardless of how many items the server has.

```python
for loc in client.locations.where(page_size=100):
    print(loc.pk, loc.name)
```

`all()` is exactly the same method under a different name — use whichever name reads better at the
call site:

```python
for loc in client.locations.all():
    print(loc.pk, loc.name)
```

Both accept the same arguments: query filters as keywords, plus a client-side `filter_fn`:

```python
active = client.deployments.where(
    page_size=50,
    filter_fn=lambda d: d.end_date is None,
)
for dep in active:
    print(dep.pk)
```

And both can be used as a context manager to stop early without exhausting the iterator:

```python
with client.locations.where(page_size=50) as query:
    first_ten = [next(query) for _ in range(10)]
```

### `find()` — a single item by PK

```python
loc = client.locations.find(42)
print(loc.name, loc.coordinates)
```

### `export()` — dump to CSV (or get plain models)

`export()` writes all results to a CSV file and returns the path:

```python
path = client.locations.export(file="locations.csv")
print(f"Saved to {path}")
```

Pass `file=None` to get a list of model instances instead — no CSV involved, just every item
fetched and parsed:

```python
records = client.deployments.export(file=None)
```

Some components validate/export a *different* schema than the one `get()`/`where()` use (e.g.
CamtrapDP-flavoured rows instead of Trapper's internal format) — that's `export_schema`, and it's
documented on each component's own page when it applies.

---

## Beyond the six patterns: component-specific methods

Several components add their own methods on top of the six above, because their underlying
endpoint needs something the generic interface can't express — a resource nested under a parent
(`client.classification_media.get_project_media(project_pk=7)`), a write operation simulating the
classic web UI (`client.locations.import_locations(...)`), or a non-paginated response shape
(`client.classification_package.get_project_package(...)`). Those are covered one component at a
time under **Component Guides** in the navigation — start there once you know *which* resource you
need; this page is about the mechanics every component shares.

!!! warning "`collection_pk` doesn't always mean the same thing"
    Some of those component-specific methods accept a `collection_pk` (or a `collection=` filter)
    that is **not** the storage collection's own pk, but the pk of an intermediate link table —
    `ClassificationProjectCollection` or `ResearchProjectCollection` — because that's what the
    server's `Classification.collection` foreign key actually points to. The parameter name is the
    same either way, so it's easy to pass the wrong pk without any error until the results come back
    empty. See [Classification Projects](guide/classification_projects.md#classified-resources-within-a-project-collection-link)
    and [Research Projects](guide/research_projects.md#collections-linked-to-a-project) for exactly
    which methods expect which pk, and how to resolve one from the other.

---

## Classification results — a worked example

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

See the [Classifications guide](guide/classifications.md) for the full picture, including
`import_classifications()`.

---

## Generic endpoint

For any endpoint not covered by a component, use `client.where()` directly:

```python
for item in client.where("api/deployments/", query={"colls": 7}):
    print(item)
```
