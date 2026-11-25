# Species

!!! info "Trapper compatibility"
    **v1** ✔ · **v2** ✔ — checked against both. See [Trapper versions](versions.md).

`client.species` — the species table of Trapper. Its PKs are the ones the `species` filter of the classification
components takes ([`classification_results`](classifications.md), [`ai_classifications`](ai_classifications.md), ...).

**Endpoint:** `GET /tables/api/species` (list + detail), paginated and ordered by English name. A Trapper v1 server
usually has the species someone added (a few); **Trapper v2 ships the whole taxonomy (36433 species)**: use a
filter rather than `get_all()`.

A row (`Species`) has `display_name` (`"Iberian lynx (Lynx pardinus)"`), `english_name`, `latin_name`, `family` and
`genus`, plus `taxon_class` and `order` on v2.

## Filters

Trapper ignores any other filter without an error — `genus=Lynx` returns every species —; the SDK emits an
`UnknownFilterWarning`.

| Parameter | Type | Description |
|---|---|---|
| `latin_name` | string | **Exact and case-sensitive** Latin name (`"Lynx pardinus"`) |
| `english_name` | string | **Exact and case-sensitive** English name (v1 `"Iberian lynx"`, v2 `"Iberian Lynx"`) |
| `search` | string | Part of the English or Latin name, any case |

## Usage

```python
lynx = client.species.get(latin_name="Lynx pardinus").results[0]
client.classification_results.get(project=2, species=lynx.pk)

for sp in client.species.where(search="fox"):
    print(sp.pk, sp.display_name)
sp = client.species.find(632)
```

!!! note "Paging"
    On the old routes the list is ordered by English name, which repeats, so its pages can repeat and skip rows:
    `where()`, `all()` and `get_all()` ask for pages of 500 and drop repeated rows, and emit an
    `UnstableOrderWarning` when the list takes more than one page (the 36433 species of v2 do). On the new API it is
    ordered by `pk`.
