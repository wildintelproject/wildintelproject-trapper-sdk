# Paquete de clasificación

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — el mismo código en ambas. Consulta [Versiones de Trapper](versions.md).

`client.classification_package` — genera (o reutiliza uno en caché) un paquete de datos Camtrap DP de
un proyecto de clasificación y devuelve su URL de descarga.

**Endpoint:** `GET /media_classification/api/package/{project_pk}/`.

!!! note "No se puede usar directamente con `get()`/`where()`"
    Es una única respuesta JSON de forma fija, no un listado paginado: usa `get_project_package()`,
    más abajo.

## Generar y descargar un paquete

```python
response = client.classification_package.get_project_package(project_pk=7)

print(response.data.message)
print(response.data.package)  # URL de descarga absoluta, ya lleva su propio token de un solo uso

file_response = client.make_request(endpoint=response.data.package, method="GET")
with open("camtrapdp_project_7.zip", "wb") as f:
    f.write(file_response.content)
```

La URL de `response.data.package` ya lleva un token de acceso de un solo uso (`?rt=...`): descárgala tal
cual con `client.make_request()`, y nunca la vuelvas a pedir a través de un método de componente.

También hay un script listo para ejecutar:
[`examples/download_camtrapdp_for_classification_project.py`](https://github.com/wildintelproject/wildintelproject-trapper-sdk/blob/refactor/examples/download_camtrapdp_for_classification_project.py).

## Parámetros de generación y caché

| Parámetro | Tipo | Por defecto | Descripción |
|---|---|---|---|
| `clear_cache` | bool | `False` | Fuerza la regeneración en lugar de reutilizar el paquete en caché |
| `release` | bool | `False` | Marca el paquete generado como una versión publicada |
| `get_released` | bool | `False` | Devuelve la última versión ya publicada |
| `export_format` | str | `"camtrapdp"` | Admite también `"trapper"` (desactiva `include_events`) |
| `export_filetype` | str | `"csv.gz"` | Formato de fichero de las tablas de datos dentro del paquete |

## Parámetros de filtrado de contenido

| Parámetro | Tipo | Por defecto | Descripción |
|---|---|---|---|
| `approved_only` | bool | `True` | Incluye solo clasificaciones aprobadas |
| `exclude_blank` | bool | `False` | Excluye observaciones en blanco |
| `all_deployments` | bool | `True` | Incluye todos los despliegues del proyecto |
| `filter_deployments` | str | `None` | PK de despliegue separadas por comas (cuando `all_deployments=False`) |
| `include_events` | bool | `False` | Incluye la tabla de eventos/secuencias |
| `events_count_var` | str | `"count"` | Nombre de la variable de recuento en la tabla de eventos |

## Parámetros de URL y privacidad de los medios

Los mismos indicadores que en [Medios de clasificación](classification_media.md):

| Parámetro | Tipo | Por defecto |
|---|---|---|
| `trapper_url_token` | bool | `True` |
| `private_human` | bool | `True` |
| `private_vehicle` | bool | `True` |
| `private_species` | list | `[]` |

## Parámetros de metadatos del paquete

Se escriben en el `datapackage.json` del paquete:

| Parámetro | Tipo | Por defecto |
|---|---|---|
| `name` | str | `None` |
| `version` | str | `"1.0"` |
| `title` | str | `None` |
| `description` | str | `None` |
| `keywords` | list | `[]` |
| `licenses` | list | `[]` |

```python
response = client.classification_package.get_project_package(
    project_pk=7,
    clear_cache=True,
    approved_only=False,
    title="Doñana camera traps 2026",
    keywords=["camera-trap", "doñana"],
)
```
