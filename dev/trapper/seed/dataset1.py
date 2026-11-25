"""First test dataset ("Mamíferos de Doñana y Sierra Morena") for a Trapper v1 or v2 test instance made by ``uv run cli trapper up``.

The small, hand-made dataset the SDK was first checked against, rebuilt from the copy kept on the old v2 test server
(``trapper-v2-sdk-v2``) so that it can be seeded on any instance. It is built like the second dataset (``dataset2.py``):
with the SDK where Trapper has a way in, and with ``manage.py shell`` where it has none.

- 6 locations (4 in Doñana, 2 in Sierra Morena) and 7 deployments, in spring 2024;
- 26 images in two collections ("Doñana primavera 2024", "Sierra Morena primavera 2024") linked to one classification
  project, "Mamíferos de Doñana y Sierra Morena" (a public Citizen Science project on v2, slug ``mamiferos-donana-sm``);
- a classificator, "Mamíferos ibéricos", with 9 species;
- 22 approved classifications by ``sdktest`` (animals with sex and age, blanks, humans) and 4 images left pending, three
  of them with classifications by ``ana`` (expert) and ``luis`` (collaborator) that disagree on the count;
- 2 AI classifications with boxes and confidence, from the provider "DeepFaune Classifier v1.2".

Usage::

    uv run python dev/trapper/seed/dataset1.py --base-url http://localhost:11180 --container wildintel-sdktest-trapper-v2-ds1-trapper-1

It prints ``DATASET1_JSON:{...}`` with the primary keys the e2e tests need.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from dataset2 import JPEG, PASSWORD, TIMEZONE, orm, retry_500, seed_client, wait
from trapper_client import TrapperClient, err
from trapper_client.schemas import ClassificationProjectCreate, ClassificatorCreate
from trapper_client.schemas.classifications import ClassificationProjectMember

PROJECT = "Mamíferos de Doñana y Sierra Morena"
SLUG = "mamiferos-donana-sm"
CLASSIFICATOR = "Mamíferos ibéricos"
AI_PROVIDER = "DeepFaune Classifier v1.2"
COLLECTIONS = {"D": "Doñana primavera 2024", "S": "Sierra Morena primavera 2024"}

SPECIES = [  # latin name, English name
    ("Genetta genetta", "Common genet"), ("Herpestes ichneumon", "Egyptian mongoose"), ("Meles meles", "European badger"),
    ("Oryctolagus cuniculus", "European rabbit"), ("Homo sapiens", "Human"), ("Lynx pardinus", "Iberian lynx"),
    ("Cervus elaphus", "Red deer"), ("Vulpes vulpes", "Red fox"), ("Sus scrofa", "Wild boar"),
]
LOCATIONS = [  # locationID, name, longitude, latitude
    ("don-01", "Doñana - Laguna del Sopetón", -6.4412, 37.0521),
    ("don-02", "Doñana - Vera de Hinojos", -6.412, 37.093),
    ("don-03", "Doñana - Cerro del Trigo", -6.478, 37.0105),
    ("don-04", "Doñana - Arroyo de la Rocina", -6.5133, 37.1204),
    ("sm-01", "Sierra Morena - Dehesa Alta", -6.152, 38.184),
    ("sm-02", "Sierra Morena - Arroyo Hondo", -6.1995, 38.221),
]
DEPLOYMENTS = [  # deploymentID, locationID, start, end (UTC), collection
    ("don01-2024a", "don-01", "2024-03-01T09:00:00", "2024-04-15T07:30:00", "D"),
    ("don01-2024b", "don-01", "2024-04-20T08:00:00", "2024-06-10T09:00:00", "D"),
    ("don02-2024a", "don-02", "2024-03-01T11:00:00", "2024-05-01T10:00:00", "D"),
    ("don03-2024a", "don-03", "2024-03-02T08:00:00", "2024-05-02T07:00:00", "D"),
    ("don04-2024a", "don-04", "2024-03-05T07:30:00", "2024-05-20T06:30:00", "D"),
    ("sm01-2024a", "sm-01", "2024-03-10T10:00:00", "2024-06-01T09:00:00", "S"),
    ("sm02-2024a", "sm-02", "2024-03-10T12:00:00", "2024-06-01T11:00:00", "S"),
]
# image, recorded (UTC), observations by sdktest: (type, species, count, sex, age); None: left pending, unclassified
IMAGES = [
    ("sm02-2024a_0003", "2024-03-10T19:49:43", [("blank", None, 1, "", "")]),
    ("don03-2024a_0001", "2024-03-12T18:19:34", [("animal", "Cervus elaphus", 1, "female", "adult")]),
    ("don02-2024a_0002", "2024-03-12T22:24:35", [("human", None, 1, "", "")]),
    ("don04-2024a_0002", "2024-03-13T03:01:19", [("animal", "Herpestes ichneumon", 1, "", "adult")]),
    ("don04-2024a_0001", "2024-03-17T03:18:59", [("animal", "Lynx pardinus", 1, "male", "adult")]),
    ("sm02-2024a_0005", "2024-03-18T23:50:16", None),
    ("don01-2024a_0004", "2024-03-19T12:30:31", [("animal", "Oryctolagus cuniculus", 1, "male", "subadult")]),
    ("don01-2024a_0003", "2024-03-22T20:33:29", [("animal", "Lynx pardinus", 2, "female", "adult")]),
    ("don03-2024a_0005", "2024-03-25T03:13:16", [("animal", "Genetta genetta", 1, "male", "adult")]),
    ("sm02-2024a_0004", "2024-03-25T11:49:34", [("animal", "Lynx pardinus", 3, "", "juvenile")]),
    ("don02-2024a_0001", "2024-03-29T23:07:19", [("animal", "Oryctolagus cuniculus", 1, "male", "subadult")]),
    ("don01-2024a_0002", "2024-04-01T01:19:00", [("animal", "Oryctolagus cuniculus", 1, "", "")]),
    ("don02-2024a_0003", "2024-04-08T07:36:02", [("animal", "Herpestes ichneumon", 1, "", "subadult")]),
    ("don01-2024a_0001", "2024-04-12T23:16:22", [("animal", "Sus scrofa", 3, "male", "")]),
    ("don03-2024a_0004", "2024-04-13T00:20:32", [("blank", None, 1, "", "")]),
    ("don03-2024a_0003", "2024-04-13T18:04:50", [("animal", "Genetta genetta", 1, "male", "subadult")]),
    ("sm01-2024a_0003", "2024-04-14T00:43:02", [("animal", "Sus scrofa", 2, "male", "adult")]),
    ("don03-2024a_0002", "2024-04-16T13:42:24", None),
    ("sm02-2024a_0001", "2024-04-17T14:40:50", [("animal", "Meles meles", 1, "", "subadult")]),
    ("don01-2024b_0001", "2024-04-22T02:11:50", [("animal", "Cervus elaphus", 4, "female", "juvenile")]),
    ("sm01-2024a_0002", "2024-05-04T12:34:13", [("animal", "Lynx pardinus", 2, "", "adult")]),
    ("don01-2024b_0003", "2024-05-09T23:05:12", None),
    ("don04-2024a_0003", "2024-05-14T12:18:06", [("animal", "Meles meles", 1, "male", "subadult")]),
    ("sm02-2024a_0002", "2024-05-15T13:21:27", [("animal", "Meles meles", 1, "", "subadult")]),
    ("sm01-2024a_0001", "2024-05-23T02:17:37", None),
    ("don01-2024b_0002", "2024-06-01T04:45:57", [("human", None, 1, "", "")]),
]
# Pending images that ana (expert) and luis (collaborator) classified: image -> (species, count by ana, count by luis)
OTHERS = {
    "don01-2024b_0003": ("Vulpes vulpes", 1, 1),
    "don03-2024a_0002": ("Sus scrofa", 2, 3),
    "sm01-2024a_0001": ("Cervus elaphus", 1, None),
}
AI_ROWS = [  # image, species, confidence, box
    ("don01-2024a_0004", "Oryctolagus cuniculus", 0.93, [0.1, 0.1, 0.3, 0.3]),
    ("don01-2024a_0003", "Lynx pardinus", 0.41, [0.5, 0.5, 0.2, 0.2]),
]
COLUMNS = ["_id", "observationType", "scientificName", "count", "sex", "lifeStage", "bboxes", "classificationMethod"]


def write_table(path: Path, rows: list[dict], extra: tuple[str, ...] = ()) -> Path:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS + list(extra))
        w.writeheader()
        for row in rows:
            w.writerow({"classificationMethod": "human", **row})
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--container", required=True, help="the app container, for what has no API")
    args = parser.parse_args()

    found = orm(args.container, """
import json
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from trapper.apps.research.models import ResearchProject
User = get_user_model()
users = {u.username: {'pk': u.pk, 'email': u.email, 'token': Token.objects.get_or_create(user=u)[0].key}
         for u in User.objects.filter(username__in=['sdktest', 'ana', 'luis'])}
print('ORM_JSON:' + json.dumps({'users': users, 'rproject': ResearchProject.objects.get(acronym='SDKT').pk}))
""")
    users, rproject = found["users"], found["rproject"]

    def client_for(username: str) -> TrapperClient:
        return seed_client(base_url=args.base_url, access_token=users[username]["token"],
                           user_name=users[username]["email"], user_password=PASSWORD, timeout=120)

    client = client_for("sdktest")
    version = client.server_version
    print(f"Trapper {version} ({client.server_release}) at {args.base_url}; research project {rproject}", flush=True)
    work = Path(tempfile.mkdtemp(prefix="dataset1-"))

    # ── species ───────────────────────────────────────────────────────────────
    species = orm(args.container, f"""
import json
from trapper.apps.extra_tables.models import Species
pks = {{}}
for latin, english in {SPECIES!r}:
    sp = Species.objects.filter(latin_name=latin).first() or Species.objects.create(latin_name=latin, english_name=english)
    pks[latin] = sp.pk
print('ORM_JSON:' + json.dumps(pks))
""")
    print(f"species: {len(species)}", flush=True)

    # ── locations and deployments (SDK imports) ───────────────────────────────
    table = work / "locations.csv"
    with table.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["locationID", "locationName", "longitude", "latitude"])
        w.writerows(LOCATIONS)
    if not {l[0] for l in LOCATIONS} <= {l.location_id for l in client.locations.where(research_project=rproject)}:
        assert retry_500(lambda: client.locations.import_locations(
            file=table, research_project=rproject, timezone=TIMEZONE)) is True
        client.locations.wait_for_import([l[0] for l in LOCATIONS], timeout=300)
    coords = {l[0]: (l[2], l[3]) for l in LOCATIONS}
    table = work / "deployments.csv"
    with table.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["deploymentID", "locationID", "longitude", "latitude", "deploymentStart", "deploymentEnd"])
        # The table's dates are local time (TIMEZONE); the source ones are UTC, two hours less in spring.
        w.writerows((d[0], d[1], *coords[d[1]], *(local(t) for t in d[2:4])) for d in DEPLOYMENTS)
    if not {d[0] for d in DEPLOYMENTS} <= {d.deployment_id for d in client.deployments.where(research_project=rproject)}:
        assert retry_500(lambda: client.deployments.import_deployments(
            file=table, research_project=rproject, timezone=TIMEZONE)) is True
        client.deployments.wait_for_import([d[0] for d in DEPLOYMENTS], timeout=300)
    print(f"locations: {len(LOCATIONS)}, deployments: {len(DEPLOYMENTS)}", flush=True)

    # ── classificator and classification project ──────────────────────────────
    members = {"ana": 2, "luis": 3}   # expert, collaborator
    if version == "v1":
        existing = {c.name: c.pk for c in client.classificators.where()}
        classificator = existing.get(CLASSIFICATOR) or client.classificators.create(ClassificatorCreate(
            name=CLASSIFICATOR, species=list(species.values()), sex=True, age=True)).pk
        # Looked up in the database: Trapper v1 caches its project list, so a project just created is not in it.
        made = orm(args.container, f"""
import json
from trapper.apps.media_classification.models import ClassificationProject
print('ORM_JSON:' + json.dumps({{'pk': getattr(ClassificationProject.objects.filter(name={PROJECT!r}).first(), 'pk', None)}}))
""")
        project = made["pk"] or client.classification_projects.create(ClassificationProjectCreate(
            name=PROJECT, research_project=rproject, classificator=classificator,
            members=[ClassificationProjectMember(user=users["ana"]["pk"], role="expert"),
                     ClassificationProjectMember(user=users["luis"]["pk"], role="collaborator")])).pk
    else:
        made = orm(args.container, f"""
import json
from django.contrib.auth import get_user_model
from trapper.apps.media_classification.models import Classificator, ClassificationProject, ClassificationProjectRole
from trapper.apps.research.models import ResearchProject
User = get_user_model()
owner = User.objects.get(username='sdktest')
cl, _ = Classificator.objects.get_or_create(name={CLASSIFICATOR!r}, defaults=dict(owner=owner, sex=True, age=True))
cl.species.set({list(species.values())!r})
p, _ = ClassificationProject.objects.get_or_create(name={PROJECT!r}, defaults=dict(
    slug={SLUG!r}, research_project=ResearchProject.objects.get(pk={rproject}), classificator=cl, owner=owner,
    status=1, citizen_science_status=1))
ClassificationProjectRole.objects.get_or_create(classification_project=p, user=owner, defaults=dict(name=1))
for username, role in {members!r}.items():
    ClassificationProjectRole.objects.get_or_create(classification_project=p, user=User.objects.get(username=username), defaults=dict(name=role))
print('ORM_JSON:' + json.dumps({{'classificator': cl.pk, 'project': p.pk}}))
""")
        classificator, project = made["classificator"], made["project"]
    print(f"classificator {classificator}, classification project {project}", flush=True)

    # ── the collection package: one package per collection, both in the same project ──
    present = {c.name: c.pk for c in client.collections.where(search="primavera 2024")}
    if not all(name in present for name in COLLECTIONS.values()):
        uploader = client.get_uploader()
        for key, name in COLLECTIONS.items():
            if name in present:
                continue
            archive, definition = work / f"dataset1{key}.zip", work / f"dataset1{key}.yaml"
            yaml = ["collections:", f"  - name: {name}", "    resources_dir: res", f"    project_id: {project}",
                    f"    timezone: {TIMEZONE}", "    timezone_ignore_dst: false", "    deployments:"]
            with zipfile.ZipFile(archive, "w") as z:
                for dep in [d for d in DEPLOYMENTS if d[4] == key]:
                    yaml += [f"      - deployment_id: {dep[0]}", "        resources:"]
                    for image, when, _ in [i for i in IMAGES if i[0].rsplit("_", 1)[0] == dep[0]]:
                        z.writestr(f"res/{dep[0]}/{image}.jpg", JPEG + image.encode())
                        yaml += [f"          - name: {image}", f"            file: {image}.jpg",
                                 f"            date_recorded: '{when}+00:00'", "            mime_type: image/jpeg"]
            definition.write_text("\n".join(yaml) + "\n", encoding="utf-8")
            uploader.upload(definition, f"collections/{definition.name}")
            uploader.upload(archive, f"collections/{archive.name}")
            for attempt in range(15):
                try:
                    retry_500(lambda: client.collections.trigger_collection(
                        {"yaml_file": definition.name, "zip_file": archive.name, "trigger_ai_pipeline": False}))
                    break
                except err.NotFoundError:
                    if attempt == 14:
                        raise
                    time.sleep(2)

        def processed() -> bool:
            names = {c.name: c.pk for c in client.collections.where(search="primavera 2024")}
            return all(n in names for n in COLLECTIONS.values()) and sum(
                client.resources.get_by_collection(names[n], page_size=1).pagination.count
                for n in COLLECTIONS.values()) >= len(IMAGES)
        wait("the collection packages", processed, timeout=900)
        present = {c.name: c.pk for c in client.collections.where(search="primavera 2024")}
    print(f"collections {present}", flush=True)

    # ── classifications: the final ones of each image, found by the image name ──
    code = ("import json\nfrom trapper.apps.media_classification.models import Classification\n"
            f"qs = Classification.objects.filter(project_id={project})\n"
            "if hasattr(Classification, 'classification_type'):\n"
            "    qs = qs.filter(classification_type='FINAL')\n"
            "print('ORM_JSON:' + json.dumps(dict(qs.values_list('resource__name', 'pk'))))\n")
    wait("the final classifications", lambda: len(orm(args.container, code)) >= len(IMAGES), timeout=600)
    finals = orm(args.container, code)

    rows = [{"_id": finals[image], "observationType": kind, "scientificName": latin or "", "count": count,
             "sex": sex, "lifeStage": age, "bboxes": ""}
            for image, _, obs in IMAGES if obs for kind, latin, count, sex, age in obs]
    done = imported(args.container, project)
    if not done.get("sdktest"):
        retry_500(lambda: client.classification_results.import_classifications(
            project_id=project, file=write_table(work / "obs-sdktest.csv", rows), approve=True))
    for n, username in enumerate(("ana", "luis")):
        if done.get(username):
            continue
        theirs = [{"_id": finals[image], "observationType": "animal", "scientificName": latin, "count": counts[n],
                   "sex": "", "lifeStage": "", "bboxes": ""}
                  for image, (latin, *counts) in OTHERS.items() if counts[n]]
        # Only a project admin may import (v1 and v2), so the member is made admin for the import and then put back.
        set_role(args.container, project, username, 1)
        try:
            retry_500(lambda: client_for(username).classification_results.import_classifications(
                project_id=project, file=write_table(work / f"obs-{username}.csv", theirs), approve=False))
        finally:
            set_role(args.container, project, username, members[username])
    print(f"observations: {len(rows)} rows by sdktest, {len(OTHERS)} images also by ana/luis", flush=True)

    # ── AI classifications ────────────────────────────────────────────────────
    provider = orm(args.container, f"""
import json
from trapper.apps.media_classification.models import AIProvider
p = AIProvider.objects.filter(name={AI_PROVIDER!r}).first() or AIProvider.objects.create(name={AI_PROVIDER!r})
print('ORM_JSON:' + json.dumps(p.pk))
""")
    box = (lambda b: json.dumps(b)) if version != "v1" else (lambda b: json.dumps([b]))
    ai = [{"_id": finals[image], "observationType": "animal", "scientificName": latin, "count": 1, "sex": "",
           "lifeStage": "", "bboxes": box(b), "classificationMethod": "machine", "classifiedBy": AI_PROVIDER,
           "classificationProbability": conf} for image, latin, conf, b in AI_ROWS]
    if not done.get("AI"):
        retry_500(lambda: client.classification_results.import_classifications(
            project_id=project, file=write_table(work / "ai.csv", ai, ("classifiedBy", "classificationProbability")),
            approve=False, import_expert_classifications=False, import_ai_classifications=True,
            ai_provider_id=provider))
    print(f"AI provider {provider}, AI rows {len(ai)}", flush=True)

    print("DATASET1_JSON:" + json.dumps({
        "version": version, "base_url": args.base_url, "token": users["sdktest"]["token"], "research_project": rproject,
        "classificator": classificator, "classification_project": project, "slug": SLUG, "collections": present,
        "species": species, "ai_provider": provider,
    }))


def imported(container: str, project: int) -> dict[str, int]:
    """How many user classifications each account has in the project, and how many AI ones (``"AI"``): a second run
    does not import them again."""
    return orm(container, f"""
import json
from django.db.models import Count
from trapper.apps.media_classification import models as m
if hasattr(m.Classification, 'classification_type'):   # v2: one table
    qs = m.Classification.objects.filter(project_id={project})
    out = dict(qs.filter(classification_type='USER').values_list('owner__username').annotate(n=Count('pk')))
    out['AI'] = qs.filter(classification_type='AI').count()
else:
    out = dict(m.UserClassification.objects.filter(classification__project_id={project})
               .values_list('owner__username').annotate(n=Count('pk')))
    out['AI'] = m.AIClassification.objects.filter(classification__project_id={project}).count()
print('ORM_JSON:' + json.dumps(out))
""")


def set_role(container: str, project: int, username: str, role: int) -> None:
    """Give an account a role in the classification project (1 admin, 2 expert, 3 collaborator)."""
    orm(container, f"""
import json
from django.contrib.auth import get_user_model
from trapper.apps.media_classification.models import ClassificationProjectRole
user = get_user_model().objects.get(username={username!r})
ClassificationProjectRole.objects.update_or_create(classification_project_id={project}, user=user, defaults=dict(name={role}))
print('ORM_JSON:' + json.dumps(True))
""")


def local(utc: str) -> str:
    """A UTC time as the wall-clock time of TIMEZONE, which is how the deployment table is read."""
    when = datetime.fromisoformat(utc).replace(tzinfo=timezone.utc).astimezone(ZoneInfo(TIMEZONE))
    return when.replace(tzinfo=None).isoformat()


if __name__ == "__main__":
    sys.exit(main())
