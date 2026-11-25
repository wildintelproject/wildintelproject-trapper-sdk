"""Schemas for User classification Trapper endpoints."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator
from trapper_client._deprecated import deprecated_getattr


class ResourceUser(BaseModel):
    """Resource entry embedded inside a User classification record."""

    pk: int
    name: str
    resource_type: str
    thumbnail_url: str
    url: str
    mime: str
    date_recorded: str
    deployment: int
    deployment_id: str


def _confidence(value: Any) -> Optional[str]:
    """A confidence as v1 writes it: a fraction with two decimals (``"0.93"``)."""
    if value is None or value == "":
        return None
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


class UserObservationAttr(BaseModel):
    """One observation of a user (or AI) classification, the same on Trapper v1 and v2.

    v1 sends each attribute as text (``"species": "Red deer (Cervus elaphus)"``) and the confidence as
    ``classification_confidence: "0.93"``. v2 wraps each one as ``{"value": ...}`` and puts the confidence, as a
    percentage, next to the value it belongs to (``{"value": "animal", "confidence": 93.0}``). Both are read into
    the v1 form: text values, and the confidence as a fraction (0-1, the scale of the ``confidence`` filter).
    A missing species, which Trapper writes as the text ``"None"``, is ``None``.
    """

    observation_type: str
    species: Optional[str] = None
    count: Optional[str] = None
    classification_confidence: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _read_trapper_attrs(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        data = dict(data)
        confidence = None
        for name in ("species", "observation_type"):
            value = data.get(name)
            if isinstance(value, dict) and value.get("confidence") is not None and confidence is None:
                confidence = float(value["confidence"]) / 100  # v2: a percentage
        for name, value in data.items():
            if isinstance(value, dict) and "value" in value:
                data[name] = value["value"]
        if data.get("classification_confidence") in (None, "") and confidence is not None:
            data["classification_confidence"] = confidence
        if "classification_confidence" in data:
            data["classification_confidence"] = _confidence(data["classification_confidence"])
        if data.get("species") in ("None", ""):
            data["species"] = None
        return data


class UserClassification(BaseModel):
    """Schema for ``/media_classification/api/user-classifications`` items.

    Fields that only one Trapper version sends are optional: ``owner_profile`` (``null`` on v2),
    ``classification`` and ``created_at`` (v1 only), ``is_setup``, ``is_feedback``, ``bboxes`` and
    ``classification_project`` (v2 only).
    """

    pk: int
    owner: str
    owner_profile: Optional[str] = None
    classification: Optional[int] = None
    resource: ResourceUser

    collection: Optional[int] = None
    updated_at: Optional[str] = None
    created_at: Optional[str] = None
    approved: Optional[bool] = None
    is_setup: Optional[bool] = None
    is_feedback: Optional[bool] = None
    bboxes: Optional[bool] = None
    classification_project: Optional[str] = None

    static_attrs: Dict[str, Any] = Field(default_factory=dict)
    dynamic_attrs: List[UserObservationAttr] = Field(default_factory=list)

    detail_data: Optional[str] = None
    delete_data: Optional[str] = None
    ai_provider: Optional[str] = None


__getattr__ = deprecated_getattr(__name__)
