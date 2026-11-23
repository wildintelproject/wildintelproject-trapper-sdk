"""
End-to-end tests for the operations that WRITE to a Trapper server: package upload and the
location / deployment / classification imports. They run against v1 and v2.

They change the server, so they are opt-in on top of the usual e2e switches:

    WILDINTEL_ALLOW_WRITE=1
    WILDINTEL_USER_NAME / WILDINTEL_USER_PASSWORD   — the imports use the session login
                                                      (an e-mail address; staff account on v2)
    WILDINTEL_RPROJECT_PK                           — research project that receives the data
    WILDINTEL_CLASSIFICATION_PROJECT_PK             — only for the classification import
    WILDINTEL_CLASSIFICATOR_PK                      — only for creating a classification project

Every location and deployment they create has a unique ID (``e2e-<random>``), so the tests can be
repeated; they do not delete what they create (the SDK has no delete for these resources).
Trapper v2 imports asynchronously, so the tests wait for the rows to show up.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from trapper_client import (
    ClassificationProjectCreate,
    ResearchProjectCreate,
    SamplingDesign,
    TrapperClient,
    err,
)

TIMEZONE = "Europe/Madrid"


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


@pytest.fixture(scope="module")
def writer() -> TrapperClient:
    if _env("WILDINTEL_ALLOW_WRITE") != "1":
        pytest.skip("Set WILDINTEL_ALLOW_WRITE=1 to run the tests that write to the server")
    if not _env("WILDINTEL_BASE_URL"):
        pytest.skip("Missing WILDINTEL_BASE_URL")
    if not _env("WILDINTEL_ACCESS_TOKEN"):
        pytest.skip("Set WILDINTEL_ACCESS_TOKEN")
    return TrapperClient(
        base_url=_env("WILDINTEL_BASE_URL"),
        access_token=_env("WILDINTEL_ACCESS_TOKEN"),
        user_name=_env("WILDINTEL_USER_NAME") or None,
        user_password=_env("WILDINTEL_USER_PASSWORD") or None,
        verify_ssl=_env("WILDINTEL_VERIFY_SSL") not in ("0", "false", "False"),
        timeout=int(_env("WILDINTEL_TIMEOUT") or 30),
    )


@pytest.fixture(scope="module")
def research_project() -> int:
    pk = _env("WILDINTEL_RPROJECT_PK")
    if not pk:
        pytest.skip("Set WILDINTEL_RPROJECT_PK")
    return int(pk)


@pytest.fixture(scope="module")
def session_writer(writer) -> TrapperClient:
    if not (_env("WILDINTEL_USER_NAME") and _env("WILDINTEL_USER_PASSWORD")):
        pytest.skip("Set WILDINTEL_USER_NAME / WILDINTEL_USER_PASSWORD (imports use the session login)")
    return writer


def _retry_once_on_500(call):
    """Run ``call()``, repeating it once if the server answers 500.

    Trapper publishes the import to celery from the web process; when RabbitMQ has dropped that
    process's idle connection, the first publish fails with a 500 and the next one works. Seen on
    v1 and v2 stacks left idle for a while (the broker logs "client unexpectedly closed TCP
    connection" at that very moment). It is the server's, not the SDK's, so the tests absorb it.
    """
    try:
        return call()
    except err.APIError as e:
        if "500" not in str(e):
            raise
        return call()


def _new_id() -> str:
    return f"e2e-{uuid.uuid4().hex[:8]}"


# ── package upload ────────────────────────────────────────────────────────────

class TestUploadE2E:

    @pytest.mark.e2e
    def test_upload_small_file(self, writer, tmp_path):
        """get_uploader() returns the uploader of the server's version and finishes an upload."""
        if writer.server_version == "v2":
            try:
                writer.upload_auth()
            except err.ForbiddenError:
                pytest.skip("this account has no HTTP uploader access (see docs/guide/versions.md)")

        payload = tmp_path / "payload.bin"
        payload.write_bytes(os.urandom(256 * 1024))
        events: list[str] = []

        uploader = writer.get_uploader(progress_callback=lambda event, data: events.append(event))
        uploader.upload(payload, f"sdk-e2e/{_new_id()}.bin")

        assert events, "the uploader reported no progress at all"

    @pytest.mark.e2e
    def test_upload_auth_matches_the_version(self, writer):
        if writer.server_version == "v2":
            assert "username" in writer.upload_auth()
        else:
            with pytest.raises(err.UnsupportedVersionError):
                writer.upload_auth()


# ── location / deployment import ──────────────────────────────────────────────

class TestLocationAndDeploymentImportE2E:

    @pytest.mark.e2e
    def test_import_locations_then_deployments(self, session_writer, research_project, tmp_path):
        loc_id, dep_id = _new_id(), _new_id()

        locations_csv = tmp_path / "locations.csv"
        locations_csv.write_text(
            "locationID,locationName,longitude,latitude\n"
            f"{loc_id},E2E location,-6.44,37.05\n",
            encoding="utf-8",
        )
        assert _retry_once_on_500(lambda: session_writer.locations.import_locations(
            file=locations_csv, research_project=research_project, timezone=TIMEZONE,
        )) is True
        session_writer.locations.wait_for_import([loc_id], timeout=90)

        deployments_csv = tmp_path / "deployments.csv"
        deployments_csv.write_text(
            "deploymentID,locationID,longitude,latitude,deploymentStart,deploymentEnd\n"
            f"{dep_id},{loc_id},-6.44,37.05,2024-03-01T10:00:00+01:00,2024-04-01T10:00:00+02:00\n",
            encoding="utf-8",
        )
        assert _retry_once_on_500(lambda: session_writer.deployments.import_deployments(
            file=deployments_csv, research_project=research_project, timezone=TIMEZONE,
        )) is True
        session_writer.deployments.wait_for_import([dep_id], timeout=90)

    @pytest.mark.e2e
    def test_import_with_a_bad_table_reports_why(self, session_writer, research_project, tmp_path):
        """A table without the mandatory columns is refused with an error naming the problem."""
        bad = tmp_path / "bad.csv"
        bad.write_text("foo,bar\n1,2\n", encoding="utf-8")

        with pytest.raises(err.APIError) as excinfo:
            session_writer.locations.import_locations(
                file=bad, research_project=research_project, timezone=TIMEZONE,
            )
        assert str(excinfo.value).strip()


# ── classification import ─────────────────────────────────────────────────────

class TestClassificationImportE2E:

    @pytest.fixture
    def project(self) -> int:
        pk = _env("WILDINTEL_CLASSIFICATION_PROJECT_PK")
        if not pk:
            pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK")
        return int(pk)

    @staticmethod
    def _existing_row(client: TrapperClient, project: int) -> dict:
        page = client.classification_results.get_project_results(project, page_size=1)
        if not page.results:
            pytest.skip("the classification project has no classifications to import into")
        return page.results[0]

    @pytest.mark.e2e
    def test_import_is_accepted(self, writer, project, tmp_path):
        """Re-importing a project's own classification, unapproved, is accepted by both versions."""
        row = self._existing_row(writer, project)
        classification_id = getattr(row, "observationID", None) or getattr(row, "classification_id", None)
        if classification_id is None:
            pytest.skip("cannot tell the classification id from this result schema")

        table = tmp_path / "observations.csv"
        table.write_text(
            "_id,observationType,scientificName,count,classificationMethod\n"
            f"{classification_id},{getattr(row, 'observationType', None) or 'animal'},"
            f"{getattr(row, 'scientificName', None) or ''},"
            f"{getattr(row, 'count', None) or 1},human\n",
            encoding="utf-8",
        )

        result = _retry_once_on_500(lambda: writer.classification_results.import_classifications(
            project_id=project, file=table, approve=False,
        ))

        assert result.data.message

    @pytest.mark.e2e
    def test_invalid_table_is_refused_locally(self, writer, project, tmp_path):
        table = tmp_path / "bad.csv"
        table.write_text("_id,sex,classificationMethod\n1,macho,human\n", encoding="utf-8")

        with pytest.raises(ValueError, match="sex"):
            writer.classification_results.import_classifications(project_id=project, file=table)


# ── research project creation (Trapper v1) ────────────────────────────────────

class TestResearchProjectCreateE2E:

    @pytest.mark.e2e
    def test_create_then_reject_a_duplicate(self, session_writer):
        if session_writer.server_version == "v2":
            with pytest.raises(err.UnsupportedVersionError):
                session_writer.research_projects.create(ResearchProjectCreate(name="e2e", acronym="e2e"))
            return

        tag = uuid.uuid4().hex[:6]
        name, acronym = f"e2e project {tag}", f"e2e{tag}"           # acronym: 9 of 10 characters
        project = session_writer.research_projects.create(ResearchProjectCreate(
            name=name, acronym=acronym, sampling_design=SamplingDesign.TARGETED, bait_use="scent",
            keywords=["e2e", "sdk"], abstract="Created by the SDK e2e tests",
        ))
        # A staff account gets the project back; any other one gets None until an admin approves it.
        if project is not None:
            assert (project.name, project.acronym) == (name, acronym)
            assert sorted(project.keywords) == ["e2e", "sdk"]

        with pytest.raises(err.APIError, match="name: .*already exists"):
            session_writer.research_projects.create(ResearchProjectCreate(name=name, acronym=f"x{tag}"))
        with pytest.raises(err.APIError, match="acronym: .*already exists"):
            session_writer.research_projects.create(ResearchProjectCreate(name=f"other {tag}", acronym=acronym))


# ── classification project creation (Trapper v1) ──────────────────────────────

class TestClassificationProjectCreateE2E:

    @pytest.mark.e2e
    def test_create_add_and_remove_a_collection(self, session_writer, research_project):
        """WILDINTEL_RPROJECT_PK must be a research project the account administers, ideally with
        collections: a classification project can only use the collections of its research project."""
        classificator = _env("WILDINTEL_CLASSIFICATOR_PK")
        if not classificator:
            pytest.skip("Set WILDINTEL_CLASSIFICATOR_PK")
        projects = session_writer.classification_projects
        if session_writer.server_version == "v2":
            with pytest.raises(err.UnsupportedVersionError):
                projects.create(ClassificationProjectCreate(name="e2e", research_project=1, classificator=1))
            return

        name = f"e2e cproject {uuid.uuid4().hex[:6]}"
        project = projects.create(ClassificationProjectCreate(
            name=name, research_project=research_project, classificator=int(classificator),
        ))
        assert project is not None and project.name == name

        collections = [
            link.collection_pk
            for link in session_writer.research_projects.where_project_collections(project_pk=research_project)
        ]
        if not collections:
            pytest.skip("the research project has no collections to link")
        pk = collections[0]

        links = projects.add_collections(project.pk, [pk])
        assert [link.collection_pk for link in links] == [pk]
        assert projects.add_collections(project.pk, [pk])[0].pk == links[0].pk      # idempotent

        assert projects.remove_collection(project.pk, pk) is True
        assert projects.find_collection_in_project(project.pk, pk) is None
        assert projects.remove_collection(project.pk, pk) is False

    @pytest.mark.e2e
    def test_unknown_research_project_is_rejected_with_the_field(self, session_writer):
        if session_writer.server_version == "v2":
            pytest.skip("Trapper v1 only")
        with pytest.raises(err.APIError, match="research_project: .*valid choice"):
            session_writer.classification_projects.create(
                ClassificationProjectCreate(name="e2e", research_project=99999999, classificator=1)
            )
