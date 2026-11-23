# Classificators

!!! info "Trapper compatibility"
    **v1** ✔ · **v2** ✔ — except `create()`, which is **v1 only**. See [Trapper versions](versions.md).

`client.classificators` — classificator configurations (the taxonomy/attribute schema a
classification project classifies against).

**Endpoint:** `GET /media_classification/api/classificators` (list + detail).

## Filters

| Parameter | Type | Description |
|---|---|---|
| `owner` | boolean | `true` = classificators owned by the user |
| `search` | string | Search by name or description |

## The six access patterns

This component has no special methods — it's exactly the generic interface described in
[Usage](../usage.md):

```python
page = client.classificators.get(page=1, page_size=50)
for classificator in client.classificators.where(owner=True):
    print(classificator)
result = client.classificators.get_all()
classificator = client.classificators.find(1)
client.classificators.export(file="classificators.csv")
```

## Creating a classificator (Trapper v1)

The REST API is read-only for classificators, so `create()` works around that by simulating the
classic web form `media_classification/classificator/create/` via cookie/session auth, like
[`import_locations()`](locations.md#importing-locations-write-access). The account that logs in
becomes the owner. On Trapper v2 it raises `UnsupportedVersionError`.

!!! warning "Not a stable API contract"
    It depends on an unversioned HTML form and needs `user_name`/`user_password` (the account's *email*
    on servers that log in by email): a token alone cannot authenticate it.

```python
from trapper_client import ClassificatorCreate

lynx = next(iter(client.species.where(search="lynx")))
classificator = client.classificators.create(
    ClassificatorCreate(
        name="Iberian mammals",
        species=[lynx, 5, 6, 7, 8],     # what a classifier can choose from: objects or primary keys
        tracked_species=[lynx],         # the ones Trapper watches
        sex=True,
        age=True,
    )
)
print(classificator.pk, classificator.name)
```

`create()` takes a `ClassificatorCreate`, a Pydantic model (a dict with its fields works too) that is
validated before anything is sent, and returns the created classificator.

| Field | Meaning | Default |
|---|---|---|
| `name` | up to 255 characters, unique | required |
| `template` | `ClassificatorTemplate.INLINE` (`"inline"`) or `TAB` (`"tab"`, tabbed): how the classification form is laid out | `INLINE` |
| `species` | the species a classifier can choose from, as objects from [`client.species`](species.md) or primary keys. Empty means **every species** | empty |
| `tracked_species` | the species Trapper **watches** (objects or primary keys): classifying one notifies the administrators of the project (an e-mail and a message). They must be among `species` when that is not empty | empty |
| `sex`, `age`, `count_new`, `behaviour`, `individual_id`, `classification_confidence` | add that optional attribute to the classification form | `False` |

Observation type, count and "is setup" are always part of the form, so they are not parameters.

!!! note "`species` and `tracked_species` are different lists"
    `species` is what a classifier *can pick*. `tracked_species` is a subset of those that Trapper
    *keeps an eye on*: the same species can be in both, but only the second one raises a notification.

!!! warning "Unknown species are dropped silently"
    Trapper ignores a species primary key that does not exist: if every key in `species` is unknown, the
    classificator is created accepting every species. Check the keys with
    [`client.species`](species.md) first when it matters.

Custom and predefined attributes (the extra fields a classificator can add to the form) are **not**
covered. A rejected form raises `APIError` naming the field, for example
`name: Classificator with this Name already exists.`; `raise_on_error=False` returns `None` instead.
