"""Second test dataset ("Cabañeros 2025") for a Trapper v1 or v2 test instance made by ``uv run cli trapper up``.

It is built with the SDK wherever Trapper has a way in (location and deployment imports, the collection package,
classificator and classification project creation on v1, the classification import), and with ``manage.py shell``
in the app container where it has none (species missing from v1, the classificator and classification projects of
v2, AI providers, roles). It differs from the first dataset on purpose:

- 12 locations and 14 deployments in Cabañeros (one shorter than a day, so the trap rates leave it out);
- 640 images in bursts of three (sequences), in two collections linked to two classification projects;
- more than 500 final classifications (paging, the unstable order of the old routes), with animals of 12 species,
  blanks, humans and vehicles (the ``private_*`` flags), counts up to 4, sex and age, one or two boxes, and some left
  unapproved or unclassified;
- AI classifications from two AI providers;
- members with different roles (``ana`` expert and ``luis`` collaborator in project A; ``plainuser`` in none).

Usage::

    uv run python dev/trapper/seed/dataset2.py --base-url http://localhost:10180 --container wildintel-sdktest-trapper-v2-p2000-trapper-1

It prints ``DATASET2_JSON:{...}`` with the primary keys the e2e tests need.
"""
from __future__ import annotations

import argparse
import base64
import csv
import json
import random
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from trapper_client import TrapperClient, err
from trapper_client.schemas import ClassificationProjectCreate, ClassificatorCreate
from trapper_client.schemas.classifications import ClassificationProjectMember

PASSWORD = "wildintel-sdk-test"
TIMEZONE = "Europe/Madrid"
RNG = random.Random(2025)

# A 1x1 JPEG; each image gets a few bytes appended so that the files differ.
JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////"
    "////////////////////////////2wBDAf//////////////////////////////////////////////////////////////////////////"
    "////////////////////////////wAARCAABAAEDASIAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAAA//EABQQAQAAAAAAAAAAAAAAAAAAAAD/"
    "xAAUAQEAAAAAAAAAAAAAAAAAAAAA/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAwDAQACEQMRAD8AP//Z"
)

SPECIES = [  # latin name, English name
    ("Cervus elaphus", "Red deer"), ("Sus scrofa", "Wild boar"), ("Lynx pardinus", "Iberian lynx"),
    ("Vulpes vulpes", "Red fox"), ("Meles meles", "European badger"), ("Genetta genetta", "Common genet"),
    ("Oryctolagus cuniculus", "European rabbit"), ("Lepus granatensis", "Granada hare"),
    ("Herpestes ichneumon", "Egyptian mongoose"), ("Capreolus capreolus", "Roe deer"),
    ("Martes foina", "Beech marten"), ("Aquila adalberti", "Spanish imperial eagle"),
]
LOCATIONS = [(f"cab-{i:02d}", f"Cabañeros {i:02d}", round(-4.62 + 0.021 * i, 5), round(39.33 + 0.013 * i, 5))
             for i in range(1, 13)]


def orm(container: str, code: str) -> dict:
    """Run ``code`` in ``manage.py shell`` of the app container; it prints ``ORM_JSON:{...}`` last."""
    result = subprocess.run(
        ["docker", "exec", "-i", "-u", "trapper", container, "python", "manage.py", "shell"],
        input=code, capture_output=True, text=True, check=False,
    )
    lines = [line for line in result.stdout.splitlines() if line.startswith("ORM_JSON:")]
    if not lines:
        raise RuntimeError(f"manage.py shell failed:\n{result.stdout[-2000:]}\n{result.stderr[-3000:]}")
    return json.loads(lines[-1][len("ORM_JSON:"):])


def seed_client(**kwargs) -> TrapperClient:
    """A client on the old routes of the server's version, also on a 2.x server with the new API (``/api/v2/``).

    Seeding is not what the tests check, and the old routes have every way in the seeds need: on 2.0.0a4 the new
    classification import answers a valid table with ``400 {"observations_csv": []}``, which the old one imports.
    """
    version = TrapperClient(**kwargs).server_version          # "v1" or "v2" (a ninja server is a v2)
    return TrapperClient(**kwargs, trapper_version=version)


def wait(what: str, check, timeout: float = 600, every: float = 5) -> None:
    deadline = time.monotonic() + timeout
    while not check():
        if time.monotonic() > deadline:
            raise TimeoutError(f"{what}: not done after {timeout:.0f}s")
        time.sleep(every)


def retry_500(call, attempts: int = 3):
    for attempt in range(attempts):
        try:
            return call()
        except err.ServerError:
            if attempt == attempts - 1:
                raise
            time.sleep(3)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--container", required=True, help="the app container, for what has no API")
    parser.add_argument("--user", default="sdktest")
    args = parser.parse_args()

    found = orm(args.container, f"""
import json
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from trapper.apps.research.models import ResearchProject
User = get_user_model()
users = {{u.username: u.pk for u in User.objects.filter(username__in=['sdktest', 'ana', 'luis', 'rp_user', 'plainuser'])}}
u = User.objects.get(username='{args.user}')
print('ORM_JSON:' + json.dumps({{'token': Token.objects.get_or_create(user=u)[0].key, 'email': u.email, 'users': users,
      'rproject': ResearchProject.objects.get(acronym='SDKT').pk}}))
""")
    client = seed_client(base_url=args.base_url, access_token=found["token"], user_name=found["email"],
                         user_password=PASSWORD, timeout=120)
    version = client.server_version
    rproject = found["rproject"]
    users = found["users"]
    print(f"Trapper {version} ({client.server_release}) at {args.base_url}; research project {rproject}", flush=True)
    work = Path(tempfile.mkdtemp(prefix="dataset2-"))

    # ── species (v1 has only the ones someone added) ──────────────────────────
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
    if not set(l[0] for l in LOCATIONS) <= {l.location_id for l in client.locations.where(research_project=rproject)}:
        assert retry_500(lambda: client.locations.import_locations(
            file=table, research_project=rproject, timezone=TIMEZONE)) is True
        client.locations.wait_for_import([l[0] for l in LOCATIONS], timeout=300)

    deployments = []
    for loc, _, lon, lat in LOCATIONS:
        start, end = "2025-04-01T08:00:00", "2025-05-15T18:00:00"
        if loc == "cab-12":
            end = "2025-04-01T18:00:00"   # shorter than a day: the trap rates leave it out
        deployments.append((f"{loc}-2025a", loc, lon, lat, start, end, "A"))
    for loc, _, lon, lat in LOCATIONS[:2]:
        deployments.append((f"{loc}-2025b", loc, lon, lat, "2025-05-20T08:00:00", "2025-06-30T18:00:00", "B"))
    table = work / "deployments.csv"
    with table.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["deploymentID", "locationID", "longitude", "latitude", "deploymentStart", "deploymentEnd"])
        w.writerows(d[:6] for d in deployments)
    if not {d[0] for d in deployments} <= {d.deployment_id for d in client.deployments.where(research_project=rproject)}:
        assert retry_500(lambda: client.deployments.import_deployments(
            file=table, research_project=rproject, timezone=TIMEZONE)) is True
        client.deployments.wait_for_import([d[0] for d in deployments], timeout=300)
    print(f"locations: {len(LOCATIONS)}, deployments: {len(deployments)}", flush=True)

    # ── classificator and classification projects ─────────────────────────────
    if version == "v1":
        existing = {c.name: c.pk for c in client.classificators.where()}
        classificator = existing.get("Cabañeros classificator") or client.classificators.create(ClassificatorCreate(
            name="Cabañeros classificator", species=list(species.values()), sex=True, age=True)).pk
        projects = {}
        # Looked up in the database: Trapper v1 caches its project list, so a project just created is not in it.
        made = orm(args.container, """
import json
from trapper.apps.media_classification.models import ClassificationProject
print('ORM_JSON:' + json.dumps({p.name: p.pk for p in ClassificationProject.objects.filter(name__startswith='Cabañeros 2025')}))
""")
        for key, name in (("A", "Cabañeros 2025 A"), ("B", "Cabañeros 2025 B")):
            mine = [type("P", (), {"pk": made[name]})] if name in made else []
            members = [ClassificationProjectMember(user=users["ana"], role="expert"),
                       ClassificationProjectMember(user=users["luis"], role="collaborator")] if key == "A" else []
            projects[key] = mine[0].pk if mine else client.classification_projects.create(ClassificationProjectCreate(
                name=name, research_project=rproject, classificator=classificator, members=members)).pk
    else:
        made = orm(args.container, f"""
import json
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from trapper.apps.media_classification.models import Classificator, ClassificationProject, ClassificationProjectRole
from trapper.apps.research.models import ResearchProject
User = get_user_model()
owner = User.objects.get(username='{args.user}')
cl, _ = Classificator.objects.get_or_create(name='Cabañeros classificator', defaults=dict(owner=owner, sex=True, age=True))
cl.species.set({list(species.values())!r})
rp = ResearchProject.objects.get(pk={rproject})
out = {{'classificator': cl.pk}}
for key, name in (('A', 'Cabañeros 2025 A'), ('B', 'Cabañeros 2025 B')):
    p, _ = ClassificationProject.objects.get_or_create(name=name, defaults=dict(
        slug=slugify(name), research_project=rp, classificator=cl, owner=owner, status=1))
    ClassificationProjectRole.objects.get_or_create(classification_project=p, user=owner, defaults=dict(name=1))
    if key == 'A':
        for username, role in (('ana', 2), ('luis', 3)):
            ClassificationProjectRole.objects.get_or_create(classification_project=p, user=User.objects.get(username=username), defaults=dict(name=role))
    out[key] = p.pk
print('ORM_JSON:' + json.dumps(out))
""")
        classificator, projects = made["classificator"], {"A": made["A"], "B": made["B"]}
    print(f"classificator {classificator}, classification projects {projects}", flush=True)

    # ── the collection package: 640 images in bursts of three ────────────────
    collections = {"A": "Cabañeros 2025 A", "B": "Cabañeros 2025 B"}
    present = {c.name: c.pk for c in client.collections.where(search="Cabañeros 2025")}
    if not all(name in present for name in collections.values()):
        per_deployment = {d[0]: (45 if d[6] == "A" else 50) for d in deployments}
        uploader = client.get_uploader()
        # One package per collection: Trapper links every collection of a package to the project of the last one.
        for key, name in collections.items():
            if name in present:
                continue
            archive, definition = work / f"cabaneros2025{key}.zip", work / f"cabaneros2025{key}.yaml"
            yaml = ["collections:", f"  - name: {name}", "    resources_dir: res", f"    project_id: {projects[key]}",
                    f"    timezone: {TIMEZONE}", "    timezone_ignore_dst: false", "    deployments:"]
            with zipfile.ZipFile(archive, "w") as z:
                for dep in [d for d in deployments if d[6] == key]:
                    yaml += [f"      - deployment_id: {dep[0]}", "        resources:"]
                    start = datetime.fromisoformat(dep[4])
                    span = (datetime.fromisoformat(dep[5]) - start).total_seconds()
                    for i in range(per_deployment[dep[0]]):
                        burst, shot = divmod(i, 3)
                        when = start + timedelta(seconds=(burst + 0.5) * span * 3 / per_deployment[dep[0]] + 7 * shot)
                        file = f"{dep[0]}_{i:03d}.jpg"
                        z.writestr(f"res/{dep[0]}/{file}", JPEG + i.to_bytes(2, "big") + dep[0].encode())
                        yaml += [f"          - name: {file[:-4]}", f"            file: {file}",
                                 f"            date_recorded: '{when.isoformat()}+02:00'",
                                 "            mime_type: image/jpeg"]
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
        total = sum(per_deployment.values())

        def processed() -> bool:
            names = {c.name: c.pk for c in client.collections.where(search="Cabañeros 2025")}
            return all(n in names for n in collections.values()) and sum(
                client.resources.get_by_collection(names[n], page_size=1).pagination.count
                for n in collections.values()) >= total
        wait("the collection package", processed, timeout=1200)
        present = {c.name: c.pk for c in client.collections.where(search="Cabañeros 2025")}
    print(f"collections {present}", flush=True)

    # ── observations: import into the final classifications of project A and B ──
    def final_pks(project: int) -> list[int]:
        # From the database: the old routes do not order the list, and past 500 rows its pages may skip some.
        code = ("import json\nfrom trapper.apps.media_classification.models import Classification\n"
                f"qs = Classification.objects.filter(project_id={project})\n"
                "if hasattr(Classification, 'classification_type'):\n"
                "    qs = qs.filter(classification_type='FINAL')\n"
                "print('ORM_JSON:' + json.dumps(sorted(qs.values_list('pk', flat=True))))\n")
        return orm(args.container, code)

    wait("the final classifications", lambda: len(final_pks(projects["A"])) >= 500, timeout=900)
    latin = [s[0] for s in SPECIES]
    rows_human, rows_ai, unapproved = [], [], []
    for key in ("A", "B"):
        for pk in final_pks(projects[key]):
            r = RNG.random()
            if r < 0.07:
                continue                      # left unclassified
            if r < 0.22:
                rows_human.append({"_id": pk, "observationType": "blank"})
            elif r < 0.27:
                rows_human.append({"_id": pk, "observationType": "human", "count": 1})
            elif r < 0.30:
                rows_human.append({"_id": pk, "observationType": "vehicle", "count": 1})
            else:
                for _ in range(2 if RNG.random() < 0.08 else 1):   # two species on some images
                    boxes = [[round(RNG.uniform(0, .6), 3), round(RNG.uniform(0, .6), 3), .2, .25]
                             for _ in range(RNG.choice([0, 0, 1, 1, 2]))]
                    row = {
                        "_id": pk, "observationType": "animal", "scientificName": RNG.choice(latin),
                        "count": RNG.choice([1, 1, 1, 2, 3, 4]),
                        "sex": RNG.choice(["", "", "female", "male"]), "lifeStage": RNG.choice(["", "adult", "juvenile"]),
                    }
                    if not boxes:
                        rows_human.append({**row, "bboxes": ""})
                    elif version == "v1":                  # v1: the boxes of an observation in one cell
                        rows_human.append({**row, "bboxes": json.dumps(boxes)})
                    else:                                  # v2: one box per row, each one individual
                        rows_human.extend({**row, "count": 1, "bboxes": json.dumps(box)} for box in boxes)
            if RNG.random() < 0.12:
                unapproved.append(pk)
            if RNG.random() < 0.10:
                rows_ai.append(pk)
    columns = ["_id", "observationType", "scientificName", "count", "sex", "lifeStage", "bboxes", "classificationMethod"]

    def write(path: Path, rows: list[dict]) -> Path:
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=columns)
            w.writeheader()
            for row in rows:
                w.writerow({"classificationMethod": "human", **row})
        return path

    for key in ("A", "B"):
        pks = set(final_pks(projects[key]))
        approved = [r for r in rows_human if r["_id"] in pks and r["_id"] not in unapproved]
        pending = [r for r in rows_human if r["_id"] in pks and r["_id"] in unapproved]
        for rows, approve in ((approved, True), (pending, False)):
            if rows:
                retry_500(lambda: client.classification_results.import_classifications(
                    project_id=projects[key], file=write(work / f"obs-{key}-{approve}.csv", rows), approve=approve))
    print(f"observations: {len(rows_human)} rows, {len(unapproved)} unapproved", flush=True)

    # ── AI classifications from two providers ─────────────────────────────────
    providers = orm(args.container, """
import json
from trapper.apps.media_classification.models import AIProvider
out = {}
for name in ('Cabañeros detector v1', 'Cabañeros species v2'):
    p = AIProvider.objects.filter(name=name).first() or AIProvider.objects.create(name=name)
    out[name] = p.pk
print('ORM_JSON:' + json.dumps(out))
""")
    pks_a = set(final_pks(projects["A"]))
    for n, (name, provider) in enumerate(providers.items()):
        rows = [{"_id": pk, "observationType": "animal", "scientificName": RNG.choice(latin), "count": 1,
                 "classificationMethod": "machine", "classifiedBy": name,
                 "classificationProbability": round(RNG.uniform(.3, .99), 2)}
                for pk in rows_ai[n::2] if pk in pks_a]
        if not rows:
            continue
        path = work / f"ai-{provider}.csv"
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=columns + ["classifiedBy", "classificationProbability"])
            w.writeheader()
            w.writerows(rows)
        retry_500(lambda: client.classification_results.import_classifications(
            project_id=projects["A"], file=path, approve=False, import_expert_classifications=False,
            import_ai_classifications=True, ai_provider_id=provider))
    print(f"AI providers {providers}, AI rows {len(rows_ai)}", flush=True)

    print("DATASET2_JSON:" + json.dumps({
        "version": version, "base_url": args.base_url, "token": found["token"], "research_project": rproject,
        "classificator": classificator, "classification_projects": projects, "collections": present,
        "species": species, "ai_providers": providers,
    }))


if __name__ == "__main__":
    sys.exit(main())
