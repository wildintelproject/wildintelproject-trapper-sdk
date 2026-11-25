"""Schemas for AI classification Trapper endpoints."""
from typing import Annotated, Any, Dict, List, Optional, Union

from pydantic import BaseModel, Discriminator, Field, Tag, field_validator

from .classifications import ClassificationResultRecordCamtrapDP, ClassificationResultRecordTrapper
from .user_classifications import UserObservationAttr
from trapper_client._deprecated import deprecated_getattr


class ResourceAI(BaseModel):
    """Resource entry embedded inside an AI classification record."""

    pk: int
    name: str
    resource_type: str
    thumbnail_url: str
    url: str
    mime: str
    date_recorded: str
    deployment: int
    deployment_id: str


class AIObservationAttr(UserObservationAttr):
    """One observation of an AI classification: see :class:`UserObservationAttr` (v1 and v2 read the same way).

    ``classification_confidence`` is the confidence of the model as a fraction (``"0.93"``) on both versions.
    """


class AIClassification(BaseModel):
    """Schema for ``/media_classification/api/ai-classifications`` items.

    Trapper v2 does not send ``owner``, ``owner_profile``, ``classification`` or ``created_at``, and may send
    ``updated_at`` as ``null``; v1 does not send ``is_setup``, ``bboxes`` or ``classification_project``.
    """

    pk: int
    owner: Optional[str] = None
    owner_profile: Optional[str] = None
    classification: Optional[int] = None

    resource: ResourceAI
    collection: Optional[int] = None

    updated_at: Optional[str] = None
    created_at: Optional[str] = None
    approved: bool
    is_setup: Optional[bool] = None
    bboxes: Optional[bool] = None
    classification_project: Optional[str] = None

    static_attrs: Dict[str, Any] = Field(default_factory=dict)
    dynamic_attrs: List[AIObservationAttr] = Field(default_factory=list)

    detail_data: Optional[str] = None
    delete_data: Optional[str] = None
    ai_provider: Optional[str] = None


class AIClassificationRecordExportCamTrap(ClassificationResultRecordCamtrapDP):
    """Camtrap DP row of the AI results table (``camtrapdp=True``, the default).

    The table has the columns of the results table of ``client.classification_results``, and is read the same
    way. Only ``observationID`` differs: Trapper v1 leaves it empty in the AI table.
    """

    observationID: Optional[int] = None

    @field_validator("observationID", mode="before")
    @classmethod
    def _empty_observation_id(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


class AIClassificationRecordExportTrapper(ClassificationResultRecordTrapper):
    """Trapper row of the AI results table (``camtrapdp=False``, with ``_id``).

    Read like the results table of ``client.classification_results``, boxes included (v1 writes a list of boxes,
    v2 one flat box).
    """


def _ai_record_kind(row: Any) -> str:
    """Only the Trapper format (``camtrapdp=False``) has an ``_id`` column."""
    if isinstance(row, dict):
        return "trapper" if "_id" in row else "camtrapdp"
    return "trapper" if isinstance(row, ClassificationResultRecordTrapper) else "camtrapdp"


AIClassificationRecordExport = Annotated[
    Union[
        Annotated[AIClassificationRecordExportCamTrap, Tag("camtrapdp")],
        Annotated[AIClassificationRecordExportTrapper, Tag("trapper")],
    ],
    Discriminator(_ai_record_kind),
]


__getattr__ = deprecated_getattr(__name__)
