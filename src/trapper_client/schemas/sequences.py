"""Schema for the Sequences Trapper endpoint."""
from typing import List, Optional

from pydantic import BaseModel, Field


class SequenceRecord(BaseModel):
    """Schema for ``/media_classification/api/sequences`` items.

    A sequence groups resources recorded within a configurable time interval
    of each other into a single event (see camtrap-dp ``eventID``).
    """

    pk: int
    sequence_id: Optional[int] = None
    sequence_uuid: str
    resources: List[int] = Field(default_factory=list)
    created_at: str
