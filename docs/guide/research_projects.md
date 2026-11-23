# Research Projects

!!! info "Trapper compatibility"
    **v1** ✔ · **v2** ✔ — except `create()`, which is **v1 only**. See [Trapper versions](versions.md).

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

## Creating a research project (Trapper v1)

The REST API is read-only for research projects, so `create()` works around that by simulating the
classic web form `research/project/create/` via cookie/session auth, like
[`import_locations()`](locations.md#importing-locations-write-access). The account that logs in
becomes the project's owner and administrator. On Trapper v2 it raises `UnsupportedVersionError`.

!!! warning "Not a stable API contract"
    It depends on an unversioned HTML form and needs `user_name`/`user_password` (the account's
    *email* on servers that log in by email) — a token alone cannot authenticate it.

```python
from trapper_client import BaitUse, ResearchProjectCreate, SamplingDesign

project = client.research_projects.create(
    ResearchProjectCreate(
        name="Doñana mammals",
        acronym="DONMAM",                       # 3 to 10 characters; name and acronym are unique
        sampling_design=SamplingDesign.TARGETED,
        bait_use=BaitUse.SCENT,
        keywords=["camera trap", "mammals"],
        abstract="Medium and large mammals of Doñana National Park.",
    )
)
print(project.pk, project.name)
```

`create()` takes a `ResearchProjectCreate`, a Pydantic model with every field of the creation form.
Building it validates the data before anything is sent: it trims the text, rejects unknown fields (a
typo fails instead of being ignored) and raises `pydantic.ValidationError`, a `ValueError`, naming the
field that is wrong. To build it from a dict (a JSON or YAML file, say), use
`ResearchProjectCreate.model_validate(data)`.

| Field | Values | Default |
|---|---|---|
| `name` | up to 255 characters, unique | required |
| `acronym` | 3 to 10 characters, unique | required |
| `sampling_design` | `SamplingDesign`: `simpleRandom` (1), `systematicRandom` (2), `clusteredRandom` (3), `experimental` (4), `targeted` (5), `opportunistic` (6) | `1` |
| `sensor_method` | `SensorMethod`: `activityDetection` (1), `timeLapse` (2), `both` (3) | `1` |
| `animal_types` | `AnimalTypes`: `unmarked` (1), `marked` (2), `both` (3) | `1` |
| `bait_use` | `BaitUse`: `none` (1), `scent` (2), `food` (3), `visual` (4), `acoustic` (5), `other` (6) | `1` |
| `event_interval` | seconds, `0` or more | `0` |
| `keywords` | list of strings; a keyword can hold spaces and commas, but not a double quote | empty |
| `abstract`, `methods`, `description` | free text, up to 2000 characters each | none |

The four choice fields have an enumeration in `trapper_client`. Its members are the integers Trapper
stores and carry the label it shows, so an editor can autocomplete them. The field accepts the
member, its number or its label, and anything else is rejected with the list of valid values:

```python
BaitUse.SCENT            # <BaitUse.SCENT: 2>
BaitUse.SCENT.label      # "scent"
ResearchProjectCreate(name="N", acronym="ABC", bait_use="scent")    # same as BaitUse.SCENT or 2
```

### Members

The creator becomes the project's administrator. `members` adds the other users that join it, each
with a role:

```python
from trapper_client import ResearchProjectCreate, ResearchProjectMember, ResearchProjectRoleType

ana = next(iter(client.users.where(search="ana")))

project = client.research_projects.create(
    ResearchProjectCreate(
        name="Doñana mammals",
        acronym="DONMAM",
        members=[
            ResearchProjectMember(user=ana, role=ResearchProjectRoleType.EXPERT),
            ResearchProjectMember(user=7, role="collaborator"),
        ],
    )
)
print([(r.username, r.roles) for r in project.project_roles])
# [('ana', ['Expert']), ('rp_staff', ['Admin']), ('user7', ['Collaborator'])]
```

- `user` is the `User` that `client.users` returns, or its primary key.
- `role` is a `ResearchProjectRoleType` (`ADMIN`, `EXPERT` or `COLLABORATOR`), its number or its label,
  in any case.
- A user cannot appear twice (the model refuses it), and the account that creates the project cannot
  be listed: it is already the administrator. Both fail before anything is sent. A user that does not
  exist is rejected by Trapper, naming the row (`project_roles-1-user: Select a valid choice.`).
- The members can only be given **when the project is created**: changing the roles of an existing
  project is a web action the SDK does not cover.

### What it returns

- **A staff account:** the project is active at once and `create()` returns it.
- **Any other account:** Trapper creates the project but keeps it *not approved*, and hides it from
  the API until an administrator approves it. `create()` then returns `None`: the project exists, it
  just cannot be read back yet.

### When the server rejects the form

A name or acronym already in use, or an acronym of the wrong length, makes Trapper re-render the
form (status `200`). `create()` raises `APIError` naming the field:

```
Research project creation failed (status 200): name: Research project with this Name already exists.
```

Pass `raise_on_error=False` to get `None` instead. What the model can check locally (empty name,
acronym length, an unknown choice, ...) raises `ValidationError` before anything is sent.
