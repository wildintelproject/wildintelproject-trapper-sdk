"""Schemas for research-project-related Trapper endpoints."""
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from trapper_client.enums import (
    AnimalTypes,
    BaitUse,
    ResearchProjectRoleType,
    SamplingDesign,
    SensorMethod,
)

from .base import TrapperSchema, choice, read_datetime
from .users import User


class ResearchProjectRole(TrapperSchema):
    """Role entry inside ``ResearchProject.project_roles``."""

    user: str | None = None
    username: str | None = None
    profile: str | None = None
    roles: list[str] = Field(default_factory=list)


class ResearchProjectCollection(TrapperSchema):
    """Schema for ``/research/api/project/{project_pk}/collections`` items."""

    pk: int
    collection_pk: int | None = None
    name: str | None = None
    owner: str | None = None
    owner_profile: str | None = None
    status: bool | int | str | None = None
    date_created: datetime | str | None = None
    description: str | None = None
    detail_data: str | None = None
    delete_data: str | None = None

    @field_validator("date_created", mode="before")
    @classmethod
    def _date(cls, v):
        """The collection's creation date, as a timezone-aware ``datetime``."""
        return read_datetime(v)


class ResearchProject(TrapperSchema):
    """Schema for ``/research/api/projects`` items."""

    pk: int
    name: str | None = None
    owner: str | None = None
    owner_profile: str | None = None
    acronym: str | None = None

    keywords: list[str] = Field(default_factory=list)
    date_created: datetime | str | None = None
    project_roles: list[ResearchProjectRole] = Field(default_factory=list)

    update_data: str | None = None
    detail_data: str | None = None
    delete_data: str | None = None

    status: bool | int | str | None = None


class ResearchProjectMember(BaseModel):
    """A user that joins a research project when it is created, and the role they have in it."""

    model_config = ConfigDict(extra="forbid")

    user: int | User = Field(description="The user the SDK returns, or their primary key.")
    role: Annotated[ResearchProjectRoleType, choice(ResearchProjectRoleType)]

    @field_validator("user")
    @classmethod
    def _primary_key(cls, value: int | User) -> int:
        pk = value if isinstance(value, int) else value.pk
        if pk <= 0:
            raise ValueError("the user primary key must be positive")
        return pk


class ResearchProjectCreate(BaseModel):
    """What it takes to create a research project (``client.research_projects.create()``).

    Trapper's REST API does not return most of these fields (see ``TRAPPER_API_IMPROVEMENTS.md``),
    so this is an input model: ``ResearchProject`` is what the API answers, this is what the
    creation form asks. The limits are the ones of Trapper's model, and unknown fields are
    rejected, so a typo fails here and not silently on the server.

    The four choice fields take an enumeration member, its number or its label::

        ResearchProjectCreate(name="Doñana mammals", acronym="DONMAM",
                               sampling_design=SamplingDesign.TARGETED, bait_use="scent")
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255, description="Unique.")
    acronym: str = Field(min_length=3, max_length=10, description="Unique.")
    sampling_design: Annotated[SamplingDesign, choice(SamplingDesign)] = SamplingDesign.SIMPLE_RANDOM
    sensor_method: Annotated[SensorMethod, choice(SensorMethod)] = SensorMethod.ACTIVITY_DETECTION
    animal_types: Annotated[AnimalTypes, choice(AnimalTypes)] = AnimalTypes.UNMARKED
    bait_use: Annotated[BaitUse, choice(BaitUse)] = BaitUse.NONE
    event_interval: int = Field(default=0, ge=0, description="Seconds.")
    keywords: list[str] = Field(default_factory=list)
    abstract: str | None = Field(default=None, max_length=2000)
    methods: str | None = Field(default=None, max_length=2000)
    description: str | None = Field(default=None, max_length=2000)
    members: list[ResearchProjectMember] = Field(
        default_factory=list,
        description="The users that join the project besides its creator, who is its administrator.",
    )

    @field_validator("keywords")
    @classmethod
    def _clean_keywords(cls, value: list[str]) -> list[str]:
        """Trim the keywords and drop the empty ones.

        A keyword may hold spaces and commas (they are sent quoted, see ``to_form()``), but not a
        double quote: Trapper cannot represent it and would drop it.
        """
        keywords = [k.strip() for k in value if k and k.strip()]
        if any('"' in k for k in keywords):
            raise ValueError("a keyword cannot contain a double quote")
        return keywords

    @field_validator("members")
    @classmethod
    def _one_role_per_user(cls, value: list[ResearchProjectMember]) -> list[ResearchProjectMember]:
        """Trapper refuses a user that appears twice in a project."""
        seen: set[int] = set()
        repeated = sorted({m.user for m in value if m.user in seen or seen.add(m.user)})
        if repeated:
            raise ValueError(f"users {repeated} appear more than once in members")
        return value

    def role_rows(self) -> list[tuple[int, int]]:
        """The members as the ``(user pk, role)`` pairs of the form's role rows."""
        return [(m.user, int(m.role)) for m in self.members]

    def to_form(self) -> dict[str, Any]:
        """The fields of Trapper's ``research/project/create/`` form, as it expects them."""
        return {
            "name": self.name,
            "acronym": self.acronym,
            "sampling_design": int(self.sampling_design),
            "sensor_method": int(self.sensor_method),
            "animal_types": int(self.animal_types),
            "bait_use": int(self.bait_use),
            "event_interval": self.event_interval,
            # each one quoted: without quotes Trapper splits "camera trap" into two keywords when it
            # is the only one (it splits on spaces when there is no comma), and on any comma
            "keywords": ", ".join(f'"{keyword}"' for keyword in self.keywords),
            "abstract": self.abstract or "",
            "methods": self.methods or "",
            "description": self.description or "",
        }
