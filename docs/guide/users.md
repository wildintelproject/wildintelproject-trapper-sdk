# Users

`client.users` — Trapper user accounts. Useful to resolve owner/user PKs (e.g. from `owner`
filters on other components) to a username or display name.

**Endpoint:** `GET /accounts/api/users` (list + detail). No server-side filters are documented for
this endpoint.

## The six access patterns

This component has no special methods and no documented filters — it's exactly the generic
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
