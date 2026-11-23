"""Schemas for Classificators Trapper endpoint."""
from typing import Annotated, Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from trapper_client.enums import ClassificatorTemplate

from .base import choice
from .species import Species
from trapper_client._deprecated import deprecated_getattr


class Classificator(BaseModel):
    """Schema for ``/api/classificators/`` items."""

    pk: int
    name: str
    owner: str
    owner_profile: Optional[str] = None  # null in Trapper v2
    updated_date: str

    predefined_attrs: Dict[str, Any] = Field(default_factory=dict)
    custom_attrs: Dict[str, Any] = Field(default_factory=dict)

    static_attrs_order: Optional[str] = None
    dynamic_attrs_order: Optional[str] = None
    description: Optional[str] = None

    update_data: Optional[str] = None
    detail_data: Optional[str] = None
    delete_data: Optional[str] = None


class ClassificatorCreate(BaseModel):
    """What it takes to create a classificator (``client.classificators.create()``).

    ``Classificator`` is what the API answers (it leaves out the species and the standard
    attributes); this is what the creation form asks. Unknown fields are rejected, so a typo fails
    here and not silently on the server.

    ``species`` limits the species a classifier can choose from (empty: every species). Both lists
    take the species themselves (``Species``, as ``client.species`` returns them) or their
    primary keys; the model keeps the primary keys.
    ``tracked_species`` are the ones Trapper watches: classifying one of them notifies the
    administrators of the project. Observation type, count and "is setup" are always on.

    Custom and predefined attributes are not part of this model.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255, description="Unique.")
    template: Annotated[ClassificatorTemplate, choice(ClassificatorTemplate)] = ClassificatorTemplate.INLINE
    species: list[int | Species] = Field(
        default_factory=list, description="Species (or their pks); empty = every species."
    )
    tracked_species: list[int | Species] = Field(
        default_factory=list, description="Species (or their pks) to watch."
    )
    sex: bool = False
    age: bool = False
    count_new: bool = False
    behaviour: bool = False
    individual_id: bool = False
    classification_confidence: bool = False

    @field_validator("species", "tracked_species")
    @classmethod
    def _primary_keys(cls, value: list[int | Species]) -> list[int]:
        """Keep the primary keys (a ``Species`` is replaced by its ``pk``), without repeats."""
        pks = [item.pk if isinstance(item, Species) else item for item in value]
        if any(pk <= 0 for pk in pks):
            raise ValueError("species primary keys must be positive")
        return list(dict.fromkeys(pks))

    @model_validator(mode="after")
    def _tracked_within_species(self) -> "ClassificatorCreate":
        extra = [pk for pk in self.tracked_species if self.species and pk not in self.species]
        if extra:
            raise ValueError(
                f"tracked_species {extra} are not in species: a classifier can only be warned about "
                "species it can choose"
            )
        return self

    def to_form(self) -> Dict[str, Any]:
        """The fields of Trapper's ``classificator/create/`` form (all prefixed ``classificator-``)."""
        data: Dict[str, Any] = {
            "classificator-name": self.name,
            "classificator-template": self.template.value,
            "classificator-species": ",".join(str(pk) for pk in self.species),
            "classificator-tracked_species": ",".join(str(pk) for pk in self.tracked_species),
        }
        for flag in ("sex", "age", "count_new", "behaviour", "individual_id", "classification_confidence"):
            if getattr(self, flag):
                data[f"classificator-{flag}"] = "on"      # a checkbox is posted only when ticked
        return data


__getattr__ = deprecated_getattr(__name__)
