# Especies

!!! info "Compatibilidad con Trapper"
    **v1** ✔ · **v2** ✔ — comprobado en los dos. Consulta [Versiones de Trapper](versions.md).

`client.species` — la tabla de especies de Trapper. Sus PK son las que recibe el filtro `species` de los
componentes de clasificación ([`classification_results`](classifications.md),
[`ai_classifications`](ai_classifications.md), ...).

**Endpoint:** `GET /tables/api/species` (listado + detalle), paginado y ordenado por nombre inglés. Un servidor
Trapper v1 suele tener las especies que alguien añadió (unas pocas); **Trapper v2 trae la taxonomía completa (36433
especies)**: usa un filtro en lugar de `get_all()`.

Una fila (`Species`) tiene `display_name` (`"Iberian lynx (Lynx pardinus)"`), `english_name`, `latin_name`, `family`
y `genus`, más `taxon_class` y `order` en v2.

## Filtros

Trapper ignora sin error cualquier otro filtro —`genus=Lynx` devuelve todas las especies—; el SDK emite un
`UnknownFilterWarning`.

| Parámetro | Tipo | Descripción |
|---|---|---|
| `latin_name` | texto | Nombre latino **exacto, distinguiendo mayúsculas** (`"Lynx pardinus"`) |
| `english_name` | texto | Nombre inglés **exacto, distinguiendo mayúsculas** (v1 `"Iberian lynx"`, v2 `"Iberian Lynx"`) |
| `search` | texto | Parte del nombre inglés o latino, sin distinguir mayúsculas |

## Uso

```python
lince = client.species.get(latin_name="Lynx pardinus").results[0]
client.classification_results.get(project=2, species=lince.pk)

for sp in client.species.where(search="fox"):
    print(sp.pk, sp.display_name)
sp = client.species.find(632)
```

!!! note "Paginación"
    En las rutas antiguas la lista se ordena por nombre inglés, que se repite, así que sus páginas pueden repetir y
    saltarse filas: `where()`, `all()` y `get_all()` piden páginas de 500, quitan las filas repetidas y emiten un
    `UnstableOrderWarning` si la lista ocupa más de una página (las 36433 especies de v2 la ocupan). En la API
    nueva se ordena por `pk`.
