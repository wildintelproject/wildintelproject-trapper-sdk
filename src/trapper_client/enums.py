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

from enum import IntEnum
from typing import Any

__all__ = ["SamplingDesign", "SensorMethod", "AnimalTypes", "BaitUse"]


class _Choice(IntEnum):
    """An ``int`` choice with the label Trapper shows for it."""

    def __new__(cls, value: int, label: str):
        member = int.__new__(cls, value)
        member._value_ = value
        member.label = label
        return member

    @classmethod
    def parse(cls, value: Any, field: str = "value") -> "_Choice":
        """Resolve a member from itself, its number, its label or its name.

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
            for member in cls:
                if value in (member.label, member.name):
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
