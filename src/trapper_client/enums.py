"""Fixed sets of values Trapper's forms accept, as enumerations.

Each member is an ``int`` (the number Trapper stores) and carries the label Trapper shows for it::

    >>> SamplingDesign.TARGETED
    <SamplingDesign.TARGETED: 5>
    >>> SamplingDesign.TARGETED.label
    'targeted'

Anywhere the SDK takes one of these (for example a ``ResearchProjectCreate``), it accepts the member,
its number or its label, so
``sampling_design=SamplingDesign.TARGETED``, ``sampling_design=5`` and ``sampling_design="targeted"``
mean the same.
"""
from __future__ import annotations

from enum import Enum, IntEnum
from typing import Any

__all__ = [
    "SamplingDesign",
    "SensorMethod",
    "AnimalTypes",
    "BaitUse",
    "ClassificatorTemplate",
    "ResearchProjectRoleType",
    "ClassificationProjectRoleType",
]


class _Choice(IntEnum):
    """An ``int`` choice with the label Trapper shows for it."""

    def __new__(cls, value: int, label: str):
        member = int.__new__(cls, value)
        member._value_ = value
        member.label = label
        return member

    @classmethod
    def parse(cls, value: Any, field: str = "value") -> "_Choice":
        """Resolve a member from itself, its number, its label or its name (in any case).

        Raises:
            ValueError: ``value`` is none of those. The message lists the valid ones.
        """
        if isinstance(value, cls):
            return value
        if isinstance(value, _Choice):
            # another enumeration's member is an int too: never take BaitUse.FOOD for SensorMethod.BOTH
            raise ValueError(f"{field}: {value!r} belongs to another enumeration, not {cls.__name__}")
        if isinstance(value, int) and not isinstance(value, bool):
            for member in cls:
                if member.value == value:
                    return member
        elif isinstance(value, str):
            wanted = value.strip().lower()
            for member in cls:
                if wanted in (member.label.lower(), member.name.lower()):
                    return member
        options = ", ".join(f"{m.label} ({m.value})" for m in cls)
        raise ValueError(f"{field}: {value!r} is not valid; use one of {options}")


class SamplingDesign(_Choice):
    """How the cameras were placed (``ResearchProject.sampling_design``)."""

    SIMPLE_RANDOM = (1, "simpleRandom")
    SYSTEMATIC_RANDOM = (2, "systematicRandom")
    CLUSTERED_RANDOM = (3, "clusteredRandom")
    EXPERIMENTAL = (4, "experimental")
    TARGETED = (5, "targeted")
    OPPORTUNISTIC = (6, "opportunistic")


class SensorMethod(_Choice):
    """What triggers a record (``ResearchProject.sensor_method``)."""

    ACTIVITY_DETECTION = (1, "activityDetection")
    TIME_LAPSE = (2, "timeLapse")
    BOTH = (3, "both")


class AnimalTypes(_Choice):
    """Whether the animals can be told apart (``ResearchProject.animal_types``)."""

    UNMARKED = (1, "unmarked")
    MARKED = (2, "marked")
    BOTH = (3, "both")


class BaitUse(_Choice):
    """The lure used (``ResearchProject.bait_use``)."""

    NONE = (1, "none")
    SCENT = (2, "scent")
    FOOD = (3, "food")
    VISUAL = (4, "visual")
    ACOUSTIC = (5, "acoustic")
    OTHER = (6, "other")


class ResearchProjectRoleType(_Choice):
    """What a user can do in a research project (``ResearchProjectRole.name``)."""

    ADMIN = (1, "Admin")
    EXPERT = (2, "Expert")
    COLLABORATOR = (3, "Collaborator")


class ClassificationProjectRoleType(_Choice):
    """What a user can do in a classification project (``ClassificationProjectRole.name``).

    ``ERROR_PROOF`` and ``CITIZEN`` belong to Trapper's citizen science features.
    """

    ADMIN = (1, "Admin")
    EXPERT = (2, "Expert")
    COLLABORATOR = (3, "Collaborator")
    ERROR_PROOF = (4, "Error proof")
    CITIZEN = (5, "Citizen")


class ClassificatorTemplate(str, Enum):
    """How a classificator's form is laid out (``Classificator.template``).

    The members are the strings Trapper stores; ``label`` is what its form shows.
    """

    INLINE = "inline"
    TAB = "tab"

    @property
    def label(self) -> str:
        return {"inline": "Inline", "tab": "Tabbed"}[self.value]

    @classmethod
    def parse(cls, value: Any, field: str = "value") -> "ClassificatorTemplate":
        """Resolve a member from itself, its value (``"tab"``), its label or its name, in any case."""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            wanted = value.strip().lower()
            for member in cls:
                if wanted in (member.value, member.name.lower(), member.label.lower()):
                    return member
        options = ", ".join(f"{m.value} ({m.label})" for m in cls)
        raise ValueError(f"{field}: {value!r} is not valid; use one of {options}")


class CollectionStatus(str, Enum):
    """Who can see a collection (``Collection.status``).

    The members are the strings Trapper stores and filters by, which are case-sensitive there (``"private"`` is an
    empty result, not an error); ``label`` is what its forms show. ``parse()`` accepts any case.
    """

    PRIVATE = "Private"
    ON_DEMAND = "OnDemand"
    PUBLIC = "Public"
    ARCHIVED = "Archived"

    @property
    def label(self) -> str:
        return {"Private": "Private", "OnDemand": "On demand", "Public": "Public", "Archived": "Archived"}[self.value]

    @classmethod
    def parse(cls, value: Any, field: str = "value") -> "CollectionStatus":
        """Resolve a member from itself, its value (``"OnDemand"``), its label or its name, in any case."""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            wanted = value.strip().lower().replace(" ", "").replace("_", "")
            for member in cls:
                if wanted in (member.value.lower(), member.name.lower().replace("_", ""), member.label.lower().replace(" ", "")):
                    return member
        options = ", ".join(f"{m.value}" for m in cls)
        raise ValueError(f"{field}: {value!r} is not valid; use one of {options}")
