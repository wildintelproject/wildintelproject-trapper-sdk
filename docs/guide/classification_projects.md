# Classification Projects

`client.classification_projects` — classification projects: the workspace where resources from one
or more collections get classified against a classificator.

**Endpoints:**

- `GET /media_classification/api/projects` (list + detail)
- `GET /media_classification/api/project/{project_pk}/collections` (collections linked to a project)
- `GET /media_classification/api/collection/{collection_pk}/resources/` (classified resources within a project-collection link)

## Filters

| Parameter | Type | Description |
|---|---|---|
| `owner` | boolean | `true` = projects where the user is owner, manager, or has *any* role |
| `status` | choice | Filter by project status |
| `research_project` | PK | Filter by research project FK |
| `search` | str | Searches across name, owner username, research project name |

## The six access patterns

```python
for proj in client.classification_projects.all():
    print(proj)

client.classification_projects.export(file="cs_projects.csv")
```

See [Usage](../usage.md) for `get()`, `get_all()`, `find()` — same interface as every component.

## Collections linked to a project

Same family of methods as [Research Projects](research_projects.md#collections-linked-to-a-project),
scoped to `/media_classification/api/project/{project_pk}/collections`:

```python
page = client.classification_projects.get_project_collections(project_pk=60)
for col in client.classification_projects.where_project_collections(project_pk=60):
    print(col)
result = client.classification_projects.get_all_project_collections(project_pk=60)

col = client.classification_projects.find_project_collection(project_pk=60, pk=35)

link_pk = client.classification_projects.find_collection_in_project(
    project_pk=60, collection_pk=47,
)
```

!!! warning "`pk`/`collection_pk` here is a *link* pk, not the storage collection pk"
    The server's `Classification.collection` foreign key points to `ClassificationProjectCollection`
    (the row linking a project to a collection), not to the storage `Collection` itself. That link
    row has its own pk, and it's what every method below expects — passing the storage collection's
    pk instead will either 404 or silently return nothing.

    **How to get the right pk:**

    - If you only know the **project** and the **storage collection pk**, resolve it with
      `find_collection_in_project(project_pk, collection_pk)` (shown above) — it iterates the
      project's links and returns the matching link pk, or `None` if that collection isn't linked
      to the project.
    - If you're already iterating `get_project_collections()`/`where_project_collections()`, each
      item's own `.pk` **is** the link pk you need — no extra lookup required.

    This same link pk is also what the `collection=` filter expects on
    [`classifications`](classifications.md), [`ai_classifications`](ai_classifications.md),
    [`user_classifications`](user_classifications.md), [`classifications_map`](classifications_map.md),
    and [`sequences`](sequences.md). The one exception is
    [`classification_media`](classification_media.md#media-scoped-to-a-collection-within-the-project),
    whose `collection_pk` *is* the real storage collection pk — it resolves the link pk for you
    internally.

## Classified resources within a project-collection link

This is the underlying data for the classification UI's resource browser: classified resources
(with sequence and approval info) inside one project-collection link.

```python
page = client.classification_projects.get_collection_resources(collection_pk=35)
for res in client.classification_projects.where_collection_resources(collection_pk=35):
    print(res)
result = client.classification_projects.get_all_collection_resources(collection_pk=35)
```

### Previous/next navigation around one resource

The server also supports a windowed, non-page-based pagination mode — the same one the classify
UI uses for "previous/next" navigation — returning up to `size` resources on each side of a given
resource, ordered by `date_recorded`:

```python
page = client.classification_projects.get_collection_resources_around(
    collection_pk=35, resource_pk=4831, size=5,
)
print(page.pagination.total, page.pagination.filtered)  # not .count/.pages here
for res in page.results:
    print(res.pk, res.name)
```
