# Research Projects

`client.research_projects` — top-level research projects; every collection and classification
project belongs to exactly one.

**Endpoints:**

- `GET /research/api/projects` (list + detail)
- `GET /research/api/project/{project_pk}/collections` (collections linked to a project)

## Filters

| Parameter | Type | Description |
|---|---|---|
| `owner` | bool | Only projects owned/managed by the current user |
| `keywords` | repeated int | Filter by keyword IDs |
| `acronym` | str | Exact acronym filter |
| `search` | str | Text search in name, acronym, abstract, owner username |
| `no-pagination` | any value | Disables pagination server-side |

## The six access patterns

```python
# One page
page = client.research_projects.get(page=1, page_size=50)
print(page.pagination, len(page.results))

# Lazy iteration (all() is the same thing)
for proj in client.research_projects.where(owner=True, acronym="WINTEL"):
    print(proj)
for proj in client.research_projects.where(search="Donana"):
    print(proj)

# CSV export
client.research_projects.export(file="research_projects.csv")
```

See [Usage](../usage.md) if any of this looks unfamiliar — it's the same interface on every component.

## Collections linked to a project

Every access pattern has a `_project_collections` counterpart, scoped to
`/research/api/project/{project_pk}/collections`:

```python
# One page
cols = client.research_projects.get_project_collections(project_pk=7)
print(cols.pagination, len(cols.results))

# Lazy iteration
for col in client.research_projects.where_project_collections(project_pk=7):
    print(col)

# Every page merged
result = client.research_projects.get_all_project_collections(project_pk=7)

# Single linked collection
col = client.research_projects.find_project_collection(project_pk=7, pk=12)
```

!!! warning "`pk` here is a *link* pk, not the storage collection pk"
    `find_project_collection`'s `pk` is the primary key of the `ResearchProjectCollection` row that
    links this project to a collection — not the storage `Collection`'s own pk. Passing the storage
    collection's pk instead will either 404 or return the wrong row.

    **How to get the right pk:**

    - If you only know the **project** and the **storage collection pk**, resolve it with
      `find_collection_in_project(project_pk, collection_pk)` below — it returns the matching link
      pk, or `None` if that collection isn't linked to the project.
    - If you're already iterating `get_project_collections()`/`where_project_collections()`, each
      item's own `.pk` **is** the link pk you need — no extra lookup required.

Check whether a specific storage collection is linked to a project, without knowing the link pk:

```python
link_pk = client.research_projects.find_collection_in_project(
    project_pk=7,
    collection_pk=42,
)
if link_pk:
    print(f"Collection 42 is linked via pk={link_pk}")
else:
    print("Collection 42 is not in this project")
```

These are thin wrappers around a nested component, `client.research_projects.collections` (an
instance of `ResearchProjectsCollectionsComponent`), which you can also use directly if you prefer:

```python
for col in client.research_projects.collections.where_project(project_pk=7):
    print(col)
```
