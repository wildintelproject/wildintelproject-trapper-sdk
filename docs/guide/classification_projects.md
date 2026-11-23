# Classification Projects

!!! info "Trapper compatibility"
    **v1** ✔ · **v2** ✔ — except `create()`, `add_collections()` and `remove_collection()`, which are **v1 only**. See [Trapper versions](versions.md).

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

## Creating a classification project (Trapper v1)

The REST API is read-only for classification projects, so `create()`, `add_collections()` and
`remove_collection()` work around that by simulating Trapper's classic web forms via cookie/session
auth, like [`import_locations()`](locations.md#importing-locations-write-access). On Trapper v2 they
raise `UnsupportedVersionError`.

!!! warning "Not a stable API contract"
    They depend on unversioned HTML forms and need `user_name`/`user_password` (the account's *email*
    on servers that log in by email): a token alone cannot authenticate them.

```python
from trapper_client import ClassificationProjectCreate

project = client.classification_projects.create(
    ClassificationProjectCreate(name="Doñana 2026", research_project=3, classificator=2)
)
print(project.pk, project.name, project.status)        # 12 Doñana 2026 Ongoing
```

`create()` takes a `ClassificationProjectCreate`, a Pydantic model. Building it validates the data before
anything is sent: a name, and the primary keys of the research project and of the classificator. To
build it from a dict, use `ClassificationProjectCreate.model_validate(data)`. The project starts *ongoing*, and the account that logs in becomes its owner and
administrator. The research project must be one the account can edit; otherwise Trapper rejects the
form and `create()` raises `APIError` naming the field:

```
Classification project creation failed (status 200): research_project: Select a valid choice. That choice is not one of the available choices.
```

It returns the created project, or `None` if it cannot be read back (or the form was rejected and
`raise_on_error=False`).

### Adding collections

A new project is empty. `add_collections()` links *storage collections* to it:

```python
links = client.classification_projects.add_collections(project.pk, [1, 2])
print([(link.pk, link.collection_pk) for link in links])
```

- The numbers you pass are the primary keys of the storage collections (`Collection.pk`), as in the
  rest of the SDK. The SDK works out the link records Trapper needs by itself.
- **A classification project can only use the collections of its research project**, and the account
  must administer that research project. A collection that is not there raises `ValueError` before
  anything is sent. Linking a collection to a research project is a web action the SDK does not cover.
- A collection that is already in the project is left as it is, so the call can be repeated.
- It returns the project's link for each collection.

### Removing a collection

```python
client.classification_projects.remove_collection(project.pk, 1)    # True; False if it was not linked
```

!!! danger "It deletes classifications"
    Unlinking is irreversible, and the classifications made on that collection **in this project are
    deleted with the link**. The collection and its resources are not touched.
