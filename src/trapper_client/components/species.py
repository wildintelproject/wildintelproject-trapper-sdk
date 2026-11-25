"""
Component for the species table of Trapper.
"""

from __future__ import annotations

from trapper_client.components.base import TrapperComponent, versioned
from trapper_client.schemas import Species

_SPECIES_FILTERS = frozenset({"english_name", "latin_name", "search", "pk"})


class SpeciesComponent(TrapperComponent[Species]):
    """
    The species table of Trapper (``client.species``). Its PKs are the ones the ``species`` filter of the
    classification components takes.

    - ``GET /tables/api/species`` (and ``/{pk}``): paginated, ordered by English name. Trapper v1 servers usually
      have the species someone added (a few); Trapper v2 ships the whole taxonomy (36433 species): use a filter.

    A row has ``display_name`` (``"Iberian lynx (Lynx pardinus)"``), ``english_name``, ``latin_name``, ``family`` and
    ``genus``, plus ``taxon_class`` and ``order`` on v2.

    **Filters** (Trapper ignores any other without an error — ``genus=Lynx`` returns every species —; the SDK emits
    an ``UnknownFilterWarning``):

    | Parameter | Type | Description |
    |---|---|---|
    | latin_name | string | **Exact and case-sensitive** Latin name (``"Lynx pardinus"``) |
    | english_name | string | **Exact and case-sensitive** English name (v1 ``"Iberian lynx"``, v2 ``"Iberian Lynx"``) |
    | search | string | Part of the English or Latin name, any case |

    Example::

        lynx = client.species.get(latin_name="Lynx pardinus").results[0]
        client.classification_results.get(project=2, species=lynx.pk)
    """

    endpoint = versioned("tables/api/species", ninja="api/v2/species/")
    schema = Species
    known_filters = {"v1": _SPECIES_FILTERS, "v2": _SPECIES_FILTERS}
