# Paquete de clasificación

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — comprobado en los dos. Consulta [Versiones de Trapper](versions.md).

`client.classification_package` — el **paquete de datos Camtrap DP** de un proyecto de clasificación: un zip con
`datapackage.json` y las tablas `deployments`, `media` y `observations` (más `events` con `include_events=True`).

**Endpoint:** `GET /media_classification/api/package/{project_pk}/`. Trapper construye el paquete en la petición
(segundos en un proyecto pequeño), o lo toma de su caché (uno por cada conjunto de parámetros; `clear_cache=True` lo
reconstruye), y responde `{"data": {"message", "errors", "package"}}`. `package` es la URL de descarga: lleva su
propio token (`?rt=...`), funciona sin el token de la API y sigue valiendo hasta que se reconstruye el paquete.

## Construir y descargar un paquete

```python
# En una llamada
ruta = client.classification_package.download_project_package(7, "doñana.zip", clear_cache=True)

# O en dos
response = client.classification_package.get_project_package(project_pk=7, approved_only=False)
print(response.data.message)
ruta = client.classification_package.download_package(response, "paquetes/")   # paquetes/<id>.zip
```

`download_package()` acepta la respuesta o su URL, descarga el zip a `<fichero>.part` y lo mueve a su sitio, y
reintenta los fallos de red. También hay un script listo para usar:
[`examples/download_camtrapdp_for_classification_project.py`](https://github.com/wildintelproject/wildintelproject-trapper-sdk/blob/development/examples/download_camtrapdp_for_classification_project.py).

## Parámetros

Trapper ignora sin error cualquier otro parámetro; el SDK emite un `UnknownFilterWarning`.

| Parámetro | Tipo | Por defecto | Descripción |
|---|---|---|---|
| `clear_cache` | bool | `False` | Reconstruir en lugar de reutilizar el paquete en caché |
| `release` | bool | `False` | Marcar el paquete como publicación |
| `get_released` | bool | `False` | Devolver la última publicación |
| `export_format` | str | `"camtrapdp"` | O `"trapper"` (columnas de Trapper; sin eventos) |
| `export_filetype` | str | `"csv.gz"` | O `"parquet"` (cualquier otro es un `400`) |
| `split_custom_attrs` | bool | `False` | **v2**, formato `"trapper"`: una columna por atributo propio (no se puede importar) |
| `approved_only` | bool | `True` | Solo clasificaciones aprobadas |
| `exclude_blank` | bool | `False` | Excluir las observaciones vacías |
| `all_deployments` | bool | `True` | Todos los despliegues del proyecto |
| `filter_deployments` | str | | Solo los despliegues cuyo `deploymentID` **contiene** este texto (no PK) |
| `include_events` | bool | `False` | Añadir la tabla de eventos (secuencias) |
| `events_count_var` | str | `"count"` | Variable de recuento de la tabla de eventos |
| `trapper_url_token`, `private_human`, `private_vehicle` | bool | `True` | Como en [media de clasificación](classification_media.md) |
| `name`, `version`, `title`, `description` | str | | Metadatos del paquete (`version` es `"1.0"`) |

!!! warning "`keywords`, `licenses` y `private_species` no se pueden enviar"
    Trapper los tipa como listas pero lee un único texto por parámetro, y siempre falla con ellos (`400`). El SDK
    lanza un `ValueError` en su lugar. El paquete toma las palabras clave del proyecto de investigación y licencias
    `private`.

!!! warning "`release` y `get_released`"
    No funcionan juntos a través de la API: una publicación construida aquí se guarda como paquete en caché, que
    `get_released` no mira; y `get_released=True` sin ninguna publicación construye un paquete nuevo junto al de la
    caché, y desde entonces Trapper responde `400 "get() returned more than one UserDataPackage"` para esos
    parámetros (`clear_cache` incluido) hasta que un administrador borra uno (admin de Django, *User data packages*).
    El error del SDK lo dice.

!!! note "v1: el proyecto necesita un administrador"
    En v1 los contribuidores del paquete son los administradores del proyecto de clasificación: un proyecto sin
    rol de administrador falla con `[] should be non-empty at property 'contributors'` (el error del SDK lo dice).

```python
response = client.classification_package.get_project_package(
    project_pk=7,
    clear_cache=True,
    approved_only=False,
    filter_deployments="don",          # deploymentID que contienen "don"
    title="Cámaras trampa de Doñana 2026",
)
```
