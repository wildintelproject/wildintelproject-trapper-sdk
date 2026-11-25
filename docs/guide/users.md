# Users

!!! info "Trapper compatibility"
    **v1** ✔ · **v2** ✔ — checked against both. See [Trapper versions](versions.md).

`client.users` — Trapper user accounts. Useful to resolve owner/user PKs (e.g. from `owner`
filters on other components) to a username or display name.

**Endpoint:** `GET /accounts/api/users` (list + detail): every account of the server, for any user with a token.
A row has `username`, `first_name`, `last_name`, `email` and `name` (the full name, or the username).

**No filters**: Trapper ignores every parameter (`search`, `username`, ...) without an error and returns every user;
the SDK emits an `UnknownFilterWarning`. Filter on the client:

```python
ana = next(client.users.where(filter_fn=lambda u: u.username == "ana"))
```

## The six access patterns

This component has no special methods and no filters — it's exactly the generic
interface described in [Usage](../usage.md):

```python
page = client.users.get(page=1, page_size=50)
for user in client.users.where():
    if user.username == "jorge.garcia":
        print(user.pk)
result = client.users.get_all()
user = client.users.find(1)
client.users.export(file="users.csv")
```

There's also a ready-to-run script showing this exact pattern (resolving a username to a pk, then
using it to filter another component):
[`examples/get_user_locations.py`](https://github.com/wildintelproject/wildintelproject-trapper-sdk/blob/refactor/examples/get_user_locations.py).
