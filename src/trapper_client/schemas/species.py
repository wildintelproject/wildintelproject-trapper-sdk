"""Schema for the Species taxonomy Trapper endpoint."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SpeciesRecord(BaseModel):
    """Schema for ``/tables/api/species`` items.

    The server serializes the model's ``__str__()`` under the literal field
    name ``__str__`` (DRF's ``SpeciesSerializer``). That name is not usable
    as a Pydantic field, so it is exposed here as ``display_name`` via an
    alias.
    """

    model_config = ConfigDict(populate_by_name=True)

    pk: int
    display_name: Optional[str] = Field(default=None, alias="__str__")
    english_name: Optional[str] = None
    latin_name: Optional[str] = None
    genus: Optional[str] = None
    family: Optional[str] = None
