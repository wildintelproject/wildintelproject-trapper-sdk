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
    WILDINTEL_MEMBER_USER_PK                        — only for creating a project with a member

Every location and deployment they create has a unique ID (``e2e-<random>``), so the tests can be
repeated; they do not delete what they create (the SDK has no delete for these resources).
Trapper v2 imports asynchronously, so the tests wait for the rows to show up.
"""
from __future__ import annotations

import base64
import os
import uuid
from pathlib import Path

import pytest

from trapper_client import (
    ClassificationProjectCreate,
    ClassificationProjectMember,
    ClassificatorCreate,
    ResearchProjectCreate,
    ResearchProjectMember,
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


# ── collection from a package ─────────────────────────────────────────────────

# A 8x8 JPEG; the second image of a package is the same one with a byte after the end of the image, which
# Trapper reads as a different file (it refuses two identical files in a deployment).
_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABALDA4MChAODQ4SERATGCgaGBYWGDEjJR0oOjM9PDkzODdASFxOQERXRTc4UG1RV19iZ2hnPk1xeXBkeFxlZ2P/"
    "2wBDARESEhgVGC8aGi9jQjhCY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2P/wAARCAAIAAgDASIAAhEBAxEB/8QAH"
    "wAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhc"
    "YGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1"
    "NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBU"
    "QdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXm"
    "JmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDFoooryz7w/9k="
)


class TestCollectionFromPackageE2E:
    """Upload a YAML and a ZIP, ``trigger_collection()`` them, and wait for the collection to show up.

    Needs an account with HTTP-uploader access (and staff on v2, for the deployment import). On v1 the
    uploader is served by Trapper's nginx, not by the app's own port. On v2 the classification project cannot be
    created by the SDK: set ``WILDINTEL_CLASSIFICATION_PROJECT_PK`` (it must belong to the research project).
    """

    @pytest.mark.e2e
    def test_upload_trigger_and_find_the_collection(self, session_writer, research_project, tmp_path):
        import time
        import zipfile

        client = session_writer
        if client.server_version == "v2":
            try:
                client.upload_auth()
            except err.ForbiddenError:
                pytest.skip("this account has no HTTP uploader access (see docs/guide/versions.md)")
            project = _env("WILDINTEL_CLASSIFICATION_PROJECT_PK")
            if not project:
                pytest.skip("Set WILDINTEL_CLASSIFICATION_PROJECT_PK (a project of the research project)")
            project = int(project)
        else:
            classificator = _env("WILDINTEL_CLASSIFICATOR_PK")
            if not classificator:
                pytest.skip("Set WILDINTEL_CLASSIFICATOR_PK to create a classification project")
            project = client.classification_projects.create(ClassificationProjectCreate(
                name=f"e2e cproject {uuid.uuid4().hex[:6]}", research_project=research_project,
                classificator=int(classificator),
            )).pk

        # a deployment of its own, to put the resources in
        tag = uuid.uuid4().hex[:8]
        deployment, location, collection = f"e2e-pkg-{tag}", f"e2e-pkgloc-{tag}", f"e2e package {tag}"
        table = tmp_path / "deployments.csv"
        table.write_text(
            "deploymentID,locationID,longitude,latitude,deploymentStart,deploymentEnd\n"
            f"{deployment},{location},-6.44,37.05,2024-03-01T00:00:00,2024-04-01T00:00:00\n",
            encoding="utf-8",
        )
        assert _retry_once_on_500(lambda: client.deployments.import_deployments(
            file=table, research_project=research_project, timezone=TIMEZONE, create_locations=True,
        )) is True
        client.deployments.wait_for_import([deployment], timeout=90)

        # the package: resources_dir/<deployment_id>/<file> in the ZIP, and the YAML that describes it
        names = [f"{deployment}_{i}.jpg" for i in range(2)]
        archive = tmp_path / f"{tag}.zip"
        with zipfile.ZipFile(archive, "w") as z:
            for i, name in enumerate(names):
                z.writestr(f"res/{deployment}/{name}", _JPEG + b"\x00" * i)
        resources = "".join(
            f"          - name: {n[:-4]}\n            file: {n}\n            date_recorded: '2024-03-0{i + 1}T10:00:00+01:00'\n"
            "            mime_type: image/jpeg\n"
            for i, n in enumerate(names)
        )
        definition = tmp_path / f"{tag}.yaml"
        definition.write_text(
            "collections:\n"
            f"  - name: {collection}\n    resources_dir: res\n    project_id: {project}\n"
            f"    timezone: {TIMEZONE}\n    timezone_ignore_dst: false\n"
            f"    deployments:\n      - deployment_id: {deployment}\n        resources:\n{resources}",
            encoding="utf-8",
        )

        uploader = client.get_uploader()
        uploader.upload(definition, f"collections/{definition.name}")
        uploader.upload(archive, f"collections/{archive.name}")

        # On v2 the files are moved into place a moment after the upload ends (tusd), so the first trigger can
        # still answer 404 "not found in your upload directory": try again for a few seconds.
        for attempt in range(10):
            try:
                response = _retry_once_on_500(lambda: client.collections.trigger_collection({
                    "yaml_file": definition.name, "zip_file": archive.name, "trigger_ai_pipeline": False,
                }))
                break
            except err.NotFoundError:
                if attempt == 9:
                    raise
                time.sleep(2)
        assert response.status_code == 200           # the task was started (task_id is None only without celery)

        deadline = time.monotonic() + 120
        found = []
        while time.monotonic() < deadline:
            found = list(client.collections.where(search=collection))
            if found and client.resources.get_by_collection(found[0].pk, page_size=1).pagination.count >= len(names):
                break
            time.sleep(3)
        assert found, "the collection did not appear"
        assert client.resources.get_by_collection(found[0].pk, page_size=5).pagination.count == len(names)

    @pytest.mark.e2e
    def test_a_package_that_is_not_on_the_server_is_not_found(self, writer):
        with pytest.raises(err.NotFoundError):
            writer.collections.trigger_collection({"yaml_file": "no-such.yaml", "zip_file": "no-such.zip"})

    @pytest.mark.e2e
    def test_a_trigger_without_files_is_a_bad_request(self, writer):
        with pytest.raises(err.BadRequestError, match="yaml_file"):
            writer.collections.trigger_collection({})


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
    def test_update_deployments_by_exporting_editing_and_importing(self, session_writer, research_project, tmp_path):
        """Export raw, edit a value, import with ``update=True`` and wait for it: the documented round trip."""
        import csv

        loc_id, dep_id = _new_id(), _new_id()
        created = tmp_path / "created.csv"
        created.write_text(
            "deploymentID,locationID,longitude,latitude,deploymentStart,deploymentEnd,cameraHeight\n"
            f"{dep_id},{loc_id},-6.44,37.05,2024-03-01T10:00:00,2024-04-01T10:00:00,0.5\n",
            encoding="utf-8",
        )
        assert _retry_once_on_500(lambda: session_writer.deployments.import_deployments(
            file=created, research_project=research_project, timezone=TIMEZONE, create_locations=True,
        )) is True
        session_writer.deployments.wait_for_import([dep_id], timeout=90)

        raw = session_writer.deployments.export(file=tmp_path / "raw.csv", raw=True, search=dep_id)
        rows = [r for r in csv.DictReader(raw.open(encoding="utf-8")) if r["deploymentID"] == dep_id]
        assert len(rows) == 1 and "_id" in rows[0]
        rows[0]["cameraHeight"] = "1.25"
        rows[0]["habitat"] = "dehesa"
        edited = tmp_path / "edited.csv"
        with edited.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

        assert _retry_once_on_500(lambda: session_writer.deployments.import_deployments(
            file=edited, research_project=research_project, timezone=TIMEZONE, update=True,
        )) is True
        session_writer.deployments.wait_for_update({dep_id: {"camera_height": 1.25, "habitat": "dehesa"}}, timeout=90)

        after = [r for r in session_writer.deployments.export(file=None, search=dep_id) if r.deployment_id == dep_id]
        assert after[0].camera_height == 1.25 and after[0].habitat == "dehesa"

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
            keywords=["e2e sdk", "tests, quoted"], abstract="Created by the SDK e2e tests",
        ))
        # A staff account gets the project back; any other one gets None until an admin approves it.
        if project is not None:
            assert (project.name, project.acronym) == (name, acronym)
            assert sorted(project.keywords) == ["e2e sdk", "tests, quoted"]

        with pytest.raises(err.APIError, match="name: .*already exists"):
            session_writer.research_projects.create(ResearchProjectCreate(name=name, acronym=f"x{tag}"))
        with pytest.raises(err.APIError, match="acronym: .*already exists"):
            session_writer.research_projects.create(ResearchProjectCreate(name=f"other {tag}", acronym=acronym))

    @pytest.mark.e2e
    def test_create_with_a_member_and_read_the_roles_back(self, session_writer):
        member = _env("WILDINTEL_MEMBER_USER_PK")
        if not member:
            pytest.skip("Set WILDINTEL_MEMBER_USER_PK (a user other than the account that logs in)")
        if session_writer.server_version == "v2":
            pytest.skip("Trapper v1 only")
        tag = uuid.uuid4().hex[:6]
        project = session_writer.research_projects.create(ResearchProjectCreate(
            name=f"e2e team {tag}", acronym=f"e2t{tag}",
            members=[ResearchProjectMember(user=int(member), role="expert")],
        ))
        if project is None:
            pytest.skip("the account is not staff: the project awaits approval and cannot be read back")
        roles = {role.username: role.roles for role in project.project_roles}
        assert ["Expert"] in roles.values() and ["Admin"] in roles.values()


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
    def test_create_with_a_member_and_read_the_roles_back(self, session_writer, research_project):
        classificator, member = _env("WILDINTEL_CLASSIFICATOR_PK"), _env("WILDINTEL_MEMBER_USER_PK")
        if not (classificator and member):
            pytest.skip("Set WILDINTEL_CLASSIFICATOR_PK and WILDINTEL_MEMBER_USER_PK")
        if session_writer.server_version == "v2":
            pytest.skip("Trapper v1 only")
        project = session_writer.classification_projects.create(ClassificationProjectCreate(
            name=f"e2e team {uuid.uuid4().hex[:6]}", research_project=research_project,
            classificator=int(classificator),
            members=[ClassificationProjectMember(user=int(member), role="collaborator")],
        ))
        roles = [role.roles for role in project.project_roles]
        assert ["Collaborator"] in roles and ["Admin"] in roles

    @pytest.mark.e2e
    def test_unknown_research_project_is_rejected_with_the_field(self, session_writer):
        if session_writer.server_version == "v2":
            pytest.skip("Trapper v1 only")
        with pytest.raises(err.APIError, match="research_project: .*valid choice"):
            session_writer.classification_projects.create(
                ClassificationProjectCreate(name="e2e", research_project=99999999, classificator=1)
            )


# ── classificator creation (Trapper v1) ───────────────────────────────────────

class TestClassificatorCreateE2E:

    @pytest.mark.e2e
    def test_create_then_reject_a_duplicate(self, session_writer):
        if session_writer.server_version == "v2":
            with pytest.raises(err.UnsupportedVersionError):
                session_writer.classificators.create(ClassificatorCreate(name="e2e"))
            return

        name = f"e2e classificator {uuid.uuid4().hex[:6]}"
        created = session_writer.classificators.create(
            ClassificatorCreate(name=name, template="tab", sex=True, age=True)
        )
        assert created is not None and created.name == name
        assert session_writer.classificators.find(created.pk).name == name
        # the optional attributes that were ticked are part of the form the classifier will see
        assert "sex" in created.dynamic_attrs_order and "age" in created.dynamic_attrs_order

        with pytest.raises(err.APIError, match="name: .*already exists"):
            session_writer.classificators.create(ClassificatorCreate(name=name))
