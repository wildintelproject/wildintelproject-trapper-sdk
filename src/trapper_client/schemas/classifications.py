"""Schemas for classification-related Trapper endpoints."""
import json
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Discriminator, Field, HttpUrl, Tag, field_validator

from trapper_client.enums import ClassificationProjectRoleType

from .base import TrapperSchema, choice, read_datetime
from .classificators import Classificator
from .research_projects import ResearchProject
from .resources import Resource
from .users import User
from trapper_client._deprecated import deprecated_getattr


class Media(TrapperSchema):
    """Schema for ``/media_classification/api/media/{project_pk}`` rows."""

    mediaID: int
    deploymentID: str
    captureMethod: str
    timestamp: datetime
    filePath: HttpUrl
    filePublic: bool
    fileName: str
    fileMediatype: str
    exifData: Optional[str] = None
    favorite: bool
    mediaComments: Optional[str] = None


class BBox(BaseModel):
    """Bounding box coordinates (normalised 0–1)."""

    x: float
    y: float
    width: float
    height: float


class ClassificationResource(BaseModel):
    """Embedded resource inside a classification record."""

    pk: int
    name: str
    resource_type: str
    thumbnail_url: str
    url: str
    mime: str
    date_recorded: datetime
    deployment: int
    deployment_id: str


class DynamicAttrValue(BaseModel):
    """A single dynamic attribute value cell."""

    value: Optional[str] = None


class DynamicAttr(BaseModel):
    """Dynamic observation attributes attached to a classification record."""

    observation_type: Optional[DynamicAttrValue] = None
    species: Optional[DynamicAttrValue] = None
    count: Optional[DynamicAttrValue] = None


class ClassificationResourceClassificationData(BaseModel):
    """Nested ``classification_data`` block inside a classification-resource row."""

    pk: int
    url: str
    is_approved: bool
    is_classified: bool


class ClassifiedResource(TrapperSchema):
    """Schema for ``/media_classification/api/collection/{collection_pk}/resources/`` items."""

    pk: int
    name: str
    thumbnail_url: str
    url: str
    mime: str
    resource_type: str
    date_recorded: datetime
    sequence: str | None = None
    classification_data: ClassificationResourceClassificationData


class ClassificationImportData(TrapperSchema):
    """Payload under ``data`` for the classification import endpoint response."""

    message: str | None = None
    errors: Any | None = None
    task_id: str | None = None


class ClassificationImportResponse(TrapperSchema):
    """Schema for ``POST /media_classification/api/classifications/import/`` responses."""

    data: ClassificationImportData | None = None


class Classification(TrapperSchema):
    """Schema for ``/media_classification/api/classifications`` items."""

    pk: int

    resource: Resource
    collection: int

    updated_at: datetime

    is_setup: bool
    static_attrs: Dict[str, Any] = {}

    dynamic_attrs: List[DynamicAttr]

    # ``status``/``status_ai`` exist in Trapper v1 only (v2 reports ``approved``); the
    # ``*_data`` UI links are ``null`` in v2.
    status: bool | None = None
    status_ai: bool | None = None
    approved: bool | None = None
    classified: bool
    classified_ai: bool

    classification_project: str

    detail_data: str | None = None
    delete_data: str | None = None
    classify_data: str | None = None
    update_data: str | None = None

    bboxes: bool


class ClassificationResultRecordCamtrapDP(TrapperSchema):
    """CamtrapDP-flavoured row from ``/media_classification/api/classifications/results/{project_pk}``."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    observationID: int
    deploymentID: str
    mediaID: int
    eventID: str
    eventStart: datetime
    eventEnd: datetime
    observationLevel: str
    observationType: str
    cameraSetupType: Optional[str] = None
    scientificName: Optional[str] = None
    count: Optional[int] = None
    lifeStage: Optional[str] = None
    sex: Optional[str] = None
    behavior: Optional[str] = None
    individualID: Optional[str] = None
    individualPositionRadius: Optional[float] = None
    individualPositionAngle: Optional[float] = None
    individualSpeed: Optional[float] = None
    bboxX: Optional[float] = None
    bboxY: Optional[float] = None
    bboxWidth: Optional[float] = None
    bboxHeight: Optional[float] = None
    classificationMethod: Optional[str] = None
    classifiedBy: Optional[str] = None
    classificationTimestamp: Optional[datetime] = None
    classificationProbability: Optional[float] = None
    observationTags: Optional[str] = None
    observationComments: Optional[str] = None

    @field_validator(
        "lifeStage", "sex", "behavior", "individualID",
        "cameraSetupType", "scientificName", "observationTags",
        "observationComments", "classificationMethod", "classifiedBy",
        mode="before",
    )
    @classmethod
    def empty_str_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator(
        "individualPositionRadius", "individualPositionAngle", "individualSpeed",
        "bboxX", "bboxY", "bboxWidth", "bboxHeight",
        "classificationProbability", "count",
        mode="before",
    )
    @classmethod
    def empty_numeric_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator("classificationTimestamp", mode="before")
    @classmethod
    def empty_datetime_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


class ClassificationResultRecordTrapper(TrapperSchema):
    """Trapper-flavoured row from ``/media_classification/api/classifications/results/{project_pk}``."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    id: int = Field(alias="_id")
    observationID: int
    deploymentID: str
    mediaID: int
    eventID: str
    eventStart: datetime
    eventEnd: datetime
    observationLevel: str
    observationType: str
    cameraSetupType: Optional[str] = None
    scientificName: Optional[str] = None
    count: Optional[int] = None
    lifeStage: Optional[str] = None
    sex: Optional[str] = None
    behavior: Optional[str] = None
    individualID: Optional[str] = None
    individualPositionRadius: Optional[float] = None
    individualPositionAngle: Optional[float] = None
    individualSpeed: Optional[float] = None
    bboxX: Optional[float] = None
    bboxY: Optional[float] = None
    bboxWidth: Optional[float] = None
    bboxHeight: Optional[float] = None
    classificationMethod: Optional[str] = None
    classifiedBy: Optional[str] = None
    classificationTimestamp: Optional[datetime] = None
    classificationProbability: Optional[float] = None
    observationTags: Optional[str] = None
    observationComments: Optional[str] = None
    countNew: Optional[int] = None
    englishName: Optional[str] = None
    bboxes: Optional[List[BBox]] = None

    @field_validator(
        "lifeStage", "sex", "behavior", "individualID", "cameraSetupType",
        "scientificName", "observationTags", "observationComments",
        "classificationMethod", "classifiedBy", "englishName",
        mode="before",
    )
    @classmethod
    def empty_str_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator(
        "individualPositionRadius", "individualPositionAngle", "individualSpeed",
        "bboxX", "bboxY", "bboxWidth", "bboxHeight",
        "classificationProbability", "count", "countNew",
        mode="before",
    )
    @classmethod
    def empty_numeric_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator("classificationTimestamp", mode="before")
    @classmethod
    def empty_datetime_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator("bboxes", mode="before")
    @classmethod
    def parse_bboxes(cls, v):
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        if isinstance(v, (str, list)):
            # The CSV has the boxes as JSON text; rows built in Python may have them as a list already.
            parsed = json.loads(v) if isinstance(v, str) else list(v)
            # Trapper can write a null among the boxes: [[x, y, w, h], null].
            if isinstance(parsed, list):
                parsed = [b for b in parsed if b is not None]
            if not parsed:
                return None
            if all(isinstance(n, (int, float)) and not isinstance(n, bool) for n in parsed) and len(parsed) == 4:
                # Trapper v2 stores one box per observation, flat: [x, y, w, h].
                return [BBox(x=parsed[0], y=parsed[1], width=parsed[2], height=parsed[3])]
            if isinstance(parsed[0], (list, type(None))):
                # Trapper v1 stores a list of boxes. It sometimes sends a null (or short) entry among them.
                boxes = [BBox(x=b[0], y=b[1], width=b[2], height=b[3])
                         for b in parsed if isinstance(b, (list, tuple)) and len(b) >= 4]
                return boxes or None
            return parsed
        return v


def _record_kind(row: Any) -> str:
    """Pick the row class by what the row is, not by which one happens to validate.

    Only the Trapper format (``camtrapdp=False``) has an ``_id`` column. Without this, a Trapper row
    that failed its own validation (a box in a shape that was not read) was accepted as the CamtrapDP
    class, which allows extra fields, and came back mistyped with no error.
    """
    if isinstance(row, dict):
        return "trapper" if "_id" in row else "camtrapdp"
    return "trapper" if isinstance(row, ClassificationResultRecordTrapper) else "camtrapdp"


ClassificationRecordExport = Annotated[
    Union[
        Annotated[ClassificationResultRecordCamtrapDP, Tag("camtrapdp")],
        Annotated[ClassificationResultRecordTrapper, Tag("trapper")],
    ],
    Discriminator(_record_kind),
]


def _empty_to_none(value: Any) -> Any:
    """An empty CSV cell is ``None``."""
    return None if isinstance(value, str) and not value.strip() else value


class ClassificationAgg(TrapperSchema):
    """A row of ``/media_classification/api/classifications/results/agg/{project_pk}/``: one deployment and species.

    The deployment's Camtrap DP fields (dates, place, camera), the days it worked (``days``), what was seen
    (``observationType``, ``scientificName``), how many (``count``, or ``countNew`` with ``count_var="countNew"``)
    and the trap rate (``trapRate`` = count / days). A deployment with no observations has one row with no species.
    Empty cells are ``None``.
    """

    deploymentID: Optional[str] = None
    locationID: Optional[str] = None
    locationName: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    coordinateUncertainty: Optional[int] = None
    deploymentStart: Optional[datetime] = None
    deploymentEnd: Optional[datetime] = None
    setupBy: Optional[str] = None
    cameraID: Optional[str] = None
    cameraModel: Optional[str] = None
    cameraDelay: Optional[int] = None
    cameraHeight: Optional[float] = None
    cameraDepth: Optional[float] = None
    cameraTilt: Optional[int] = None
    cameraHeading: Optional[int] = None
    detectionDistance: Optional[float] = None
    timestampIssues: Optional[bool] = None
    baitUse: Optional[bool] = None
    featureType: Optional[str] = None
    habitat: Optional[str] = None
    deploymentGroups: Optional[str] = None
    deploymentTags: Optional[str] = None
    deploymentComments: Optional[str] = None
    days: Optional[int] = None
    observationType: Optional[str] = None
    scientificName: Optional[str] = None
    count: Optional[int] = None
    countNew: Optional[int] = None
    trapRate: Optional[float] = None

    @field_validator("*", mode="before")
    @classmethod
    def _empty_cell(cls, v):
        return _empty_to_none(v)

    @field_validator("deploymentStart", "deploymentEnd", mode="before")
    @classmethod
    def _date(cls, v):
        return read_datetime(v)


class ResultsDataPackageData(TrapperSchema):
    """Payload under ``data`` for package generation endpoint responses."""

    message: str | None = None
    errors: Any | None = None
    package: str | None = None


class ResultsDataPackageResponse(TrapperSchema):
    """Schema for ``/media_classification/api/package/{project_pk}`` responses."""

    data: ResultsDataPackageData | None = None


class TrapperClassificationProjectRole(BaseModel):
    """Role entry inside a classification project."""

    user: str
    profile: str | None = None  # null in Trapper v2
    roles: List[str]


class ClassificationProject(TrapperSchema):
    """Schema for ``/api/cs/projects/`` items."""

    pk: int
    name: str
    owner: str
    owner_profile: str | None = None  # null in Trapper v2
    classificator: int
    research_project: str
    status: str
    is_active: bool
    project_roles: List[TrapperClassificationProjectRole]
    classificator_removed: bool
    update_data: str | None = None
    detail_data: str | None = None
    delete_data: str | None = None


class ClassificationProjectMember(BaseModel):
    """A user that joins a classification project when it is created, and their role in it."""

    model_config = ConfigDict(extra="forbid")

    user: int | User = Field(description="The user the SDK returns, or their primary key.")
    role: Annotated[ClassificationProjectRoleType, choice(ClassificationProjectRoleType)]

    @field_validator("user")
    @classmethod
    def _primary_key(cls, value: int | User) -> int:
        pk = value if isinstance(value, int) else value.pk
        if pk <= 0:
            raise ValueError("the user primary key must be positive")
        return pk


class ClassificationProjectCreate(BaseModel):
    """What it takes to create a classification project
    (``client.classification_projects.create()``).

    ``ClassificationProject`` is what the API answers (it names the research project, not its pk);
    this is what the creation form asks. Unknown fields are rejected, so a typo fails here and not
    silently on the server.

    The research project and the classificator can be given as the objects the SDK returns
    (``ResearchProject``, ``Classificator``) or as their primary keys; the model keeps the
    primary keys.

    The project starts *ongoing*, and the account that creates it becomes its owner and
    administrator. Collections are added afterwards with ``add_collections()``.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    research_project: int | ResearchProject = Field(description="The research project, or its primary key.")
    classificator: int | Classificator = Field(description="The classificator, or its primary key.")
    members: List[ClassificationProjectMember] = Field(
        default_factory=list,
        description="The users that join the project besides its creator, who is its administrator.",
    )

    @field_validator("research_project", "classificator")
    @classmethod
    def _primary_key(cls, value: int | ResearchProject | Classificator) -> int:
        """Keep the primary key (an object is replaced by its ``pk``)."""
        pk = value if isinstance(value, int) else value.pk
        if pk <= 0:
            raise ValueError("the primary key must be positive")
        return pk

    @field_validator("members")
    @classmethod
    def _one_role_per_user(cls, value: List[ClassificationProjectMember]) -> List[ClassificationProjectMember]:
        """Trapper refuses a user that appears twice in a project."""
        seen: set = set()
        repeated = sorted({m.user for m in value if m.user in seen or seen.add(m.user)})
        if repeated:
            raise ValueError(f"users {repeated} appear more than once in members")
        return value

    def role_rows(self) -> List[tuple]:
        """The members as the ``(user pk, role)`` pairs of the form's role rows."""
        return [(m.user, int(m.role)) for m in self.members]

    def to_form(self) -> Dict[str, Any]:
        """The fields of Trapper's ``media_classification/project/create/`` form."""
        return {
            "name": self.name,
            "research_project": self.research_project,
            "classificator": self.classificator,
            "status": 1,  # ongoing: the form hides the field and posts this value on creation
        }


class ClassificationProjectCollection(TrapperSchema):
    """Schema for collection entries inside a classification project."""

    pk: int
    collection_pk: int
    name: str
    status: str
    is_active: bool
    detail_data: str | None = None
    classify_data: str | None = None
    approved_count: int = 0
    classified_count: int = 0
    total_count: int = 0


__getattr__ = deprecated_getattr(__name__)
