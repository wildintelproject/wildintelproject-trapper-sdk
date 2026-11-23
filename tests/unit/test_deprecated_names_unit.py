"""The schemas lost their ``Record`` suffix; the old names still work and warn."""
from __future__ import annotations

import importlib
import warnings

import pytest

import trapper_client
from trapper_client._deprecated import RENAMED_SCHEMAS
from trapper_client import schemas

# the module that defines each renamed schema
DEFINED_IN = {
    "User": "users",
    "Species": "species",
    "Sequence": "sequences",
    "Map": "maps",
    "Classificator": "classificators",
    "Classification": "classifications",
    "UserClassification": "user_classifications",
    "AIClassification": "ai_classifications",
    "ClassificationMap": "classifications_map",
    "ClassificationAgg": "classifications",
    "ClassifiedResource": "classifications",
    "Media": "classifications",
}


def test_every_renamed_schema_has_a_defining_module():
    assert set(DEFINED_IN) == set(RENAMED_SCHEMAS.values())


@pytest.mark.parametrize("old, new", RENAMED_SCHEMAS.items())
class TestOldNames:

    def test_the_new_name_is_the_class(self, old, new):
        module = importlib.import_module(f"trapper_client.schemas.{DEFINED_IN[new]}")
        assert getattr(module, new).__name__ == new

    @pytest.mark.parametrize("where", ["package", "schemas", "module"])
    def test_the_old_name_warns_and_is_the_same_class(self, old, new, where):
        module = {
            "package": trapper_client,
            "schemas": schemas,
            "module": importlib.import_module(f"trapper_client.schemas.{DEFINED_IN[new]}"),
        }[where]
        with pytest.warns(DeprecationWarning, match=f"{old} is deprecated.*use {new}"):
            alias = getattr(module, old)
        assert alias is getattr(module, new)

    def test_the_old_name_is_not_offered_by_a_star_import(self, old, new):
        assert old not in trapper_client.__all__ and old not in schemas.__all__
        assert new in trapper_client.__all__


def test_an_unknown_name_is_still_an_error():
    with pytest.raises(AttributeError):
        trapper_client.NopeRecord
    with pytest.raises(ImportError):
        from trapper_client.schemas import NopeRecord  # noqa: F401


def test_a_module_does_not_answer_for_a_schema_it_does_not_define():
    users = importlib.import_module("trapper_client.schemas.users")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(AttributeError):
            users.SpeciesRecord
