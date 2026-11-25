"""Schema for the Sequences Trapper endpoint."""
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator
from trapper_client._deprecated import deprecated_getattr


class Sequence(BaseModel):
    """Schema for ``/media_classification/api/sequences`` items.

    A sequence groups resources recorded within a configurable time interval
    of each other into a single event (see camtrap-dp ``eventID``).
    """

    pk: int
    sequence_id: Optional[int] = None
    sequence_uuid: str
    resources: List[int] = Field(default_factory=list)
    created_at: str

    @field_validator("resources", mode="before")
    @classmethod
    def _once_each(cls, v):
        """Trapper v2 repeats a resource once per classification of it (final, user, AI): keep the first."""
        if isinstance(v, list):
            return list(dict.fromkeys(v))
        return v


__getattr__ = deprecated_getattr(__name__)
