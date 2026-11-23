# Usuarios

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — el mismo código en ambas. Consulta [Versiones de Trapper](versions.md).

`client.users` — cuentas de usuario de Trapper. Útil para traducir PK de propietario o usuario (por
ejemplo, de los filtros `owner` de otros componentes) a un nombre de usuario o nombre visible.

**Endpoint:** `GET /accounts/api/users` (listado + detalle). Este endpoint no tiene filtros de servidor
documentados.

## Los seis patrones de acceso

Este componente no tiene métodos especiales ni filtros documentados: es exactamente la interfaz
genérica descrita en [Uso](../usage.md):

```python
page = client.users.get(page=1, page_size=50)
for user in client.users.where():
    if user.username == "jorge.garcia":
        print(user.pk)
result = client.users.get_all()
user = client.users.find(1)
client.users.export(file="users.csv")
```

También hay un script listo para ejecutar que muestra este mismo patrón (traducir un nombre de usuario
a una pk y usarla para filtrar otro componente):
[`examples/get_user_locations.py`](https://github.com/wildintelproject/wildintelproject-trapper-sdk/blob/refactor/examples/get_user_locations.py).
