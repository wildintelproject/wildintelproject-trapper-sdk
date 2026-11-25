"""Print the ``WILDINTEL_*`` variables the e2e tests need for a seeded test instance (dataset 1 or 2).

The primary keys are read through the SDK (the first row of each list), so they are the ones the API shows; the
classification project and the collection are the dataset's own. Usage::

    eval "$(uv run cli trapper env v2 --dataset 1)"      # through the CLI
    eval "$(uv run python dev/trapper/seed/e2e_env.py --instance v2 --dataset 1)"

``--instance`` is the folder of ``dev/trapper/.state`` (``v1-ds1``, ``v2-p2000``, ...); its ``seed.json`` and ``.env``
give the token, the password and the port.
"""
from __future__ import annotations

import argparse
import json
import shlex
import sys
import warnings
from pathlib import Path

from trapper_client import TrapperClient

STATE = Path(__file__).resolve().parents[1] / ".state"
DATASETS = {  # classification project, its collection, the Citizen Science slug (v2)
    "1": ("Mamíferos de Doñana y Sierra Morena", "Doñana primavera 2024", "mamiferos-donana-sm"),
    "2": ("Cabañeros 2025 A", "Cabañeros 2025 A", None),
}


def first_pk(fetch) -> int | None:
    """The pk of the first row a list call returns, or None when it fails or is empty."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            items = fetch().results
    except Exception:  # noqa: BLE001 - an endpoint the version lacks: the tests that need it skip
        return None
    if not items:
        return None
    item = items[0]
    return getattr(item, "pk", None) or getattr(item, "id", None) or (item.get("pk") if isinstance(item, dict) else None)


def variables(instance: str, dataset: str) -> dict[str, object]:
    """The ``WILDINTEL_*`` variables for the e2e tests on ``instance`` (a folder of ``dev/trapper/.state``) seeded
    with ``dataset`` (``"1"`` or ``"2"``); ``None`` for one the instance cannot give (the tests that need it skip)."""
    folder = STATE / instance
    seed = json.loads((folder / "seed.json").read_text())
    env = dict(line.split("=", 1) for line in (folder / ".env").read_text().splitlines() if "=" in line and line[0] != "#")
    base_url = f"http://localhost:{env['NGINX_PORT']}"
    token, password = seed["tokens"]["sdktest"], seed["password"]
    client = TrapperClient(base_url=base_url, access_token=token, user_name="sdktest@example.org",
                           user_password=password, timeout=120)
    project_name, collection_name, slug = DATASETS[dataset]

    project = next(p for p in client.classification_projects.where() if p.name == project_name)
    collection = next(c for c in client.collections.where(search=collection_name) if c.name == collection_name)
    rproject = seed["research_project"]
    media = None
    try:
        page = client.classification_media.get_project_media(project.pk, page_size=1)
        media = client.classification_media._extract_media_id(page.results[0]) if page.results else None
    except Exception:  # noqa: BLE001
        pass
    # A resource of the collection and the location it was taken at: the tests look it up by both.
    in_collection = {r.pk for r in client.resources.get_all_by_collection(collection.pk).results}
    location = resource = None
    for loc in client.locations.where(research_project=rproject):
        hits = [r.pk for r in client.resources.get_all_by_location(loc.pk).results if r.pk in in_collection]
        if hits:
            location, resource = loc.pk, min(hits)
            break
    users = {u.username: u.pk for u in client.users.where()}

    return {
        "WILDINTEL_BASE_URL": base_url,
        "WILDINTEL_ACCESS_TOKEN": token,
        "WILDINTEL_USER_NAME": "sdktest@example.org",
        "WILDINTEL_USER_PASSWORD": password,
        "WILDINTEL_SMOKE_ENABLED": "1",
        "WILDINTEL_ALLOW_WRITE": "1",
        "WILDINTEL_RPROJECT_PK": rproject,
        "WILDINTEL_PROJECT_PK": project.pk,
        "WILDINTEL_CLASSIFICATION_PROJECT_PK": project.pk,
        "WILDINTEL_COLLECTION_PK": collection.pk,
        "WILDINTEL_CLASSIFICATION_COLLECTION_PK": collection.pk,
        "WILDINTEL_CLASSIFICATION_LINK_PK": first_pk(lambda: client.classification_projects.get_project_collections(
            project_pk=project.pk, page_size=1)),
        "WILDINTEL_RPROJECT_COLLECTION": first_pk(lambda: client.research_projects.get_project_collections(
            project_pk=rproject, page_size=1)),
        "WILDINTEL_LOCATION_PK": location,
        "WILDINTEL_DEPLOYMENT_PK": first_pk(lambda: client.deployments.get(page_size=1)),
        "WILDINTEL_RESOURCE_PK": resource,
        "WILDINTEL_MEDIA_ID": media,
        "WILDINTEL_CLASSIFICATION_RESULT_PK": first_pk(lambda: client.classification_results.get_project_results(
            project.pk, page_size=1)),
        "WILDINTEL_USER_CLASSIFICATION_PK": first_pk(lambda: client.user_classifications.get(
            project=project.pk, page_size=1)),
        "WILDINTEL_AI_CLASSIFICATION_PK": first_pk(lambda: client.ai_classifications.get(
            project=project.pk, page_size=1)),
        "WILDINTEL_CLASSIFICATOR_PK": project.classificator if isinstance(project.classificator, int) else first_pk(
            lambda: client.classificators.get(page_size=1)),
        "WILDINTEL_SPECIES_PK": first_pk(lambda: client.species.get(page_size=1)),
        "WILDINTEL_SEQUENCE_PK": first_pk(lambda: client.sequences.get(page_size=1)),
        "WILDINTEL_MAP_PK": first_pk(lambda: client.maps.get(page_size=1)),
        "WILDINTEL_CLASSIFICATIONS_MAP_PK": first_pk(lambda: client.classifications_map.get(page_size=1)),
        "WILDINTEL_USER_PK": users.get("sdktest") or first_pk(lambda: client.users.get(page_size=1)),
        "WILDINTEL_MEMBER_USER_PK": users.get("ana"),
        # The citizen science project deployments: only the SDK's v2 component (the dataset makes it CS on v2).
        "WILDINTEL_PROJECT_SLUG": slug if client.server_version != "v1" else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--instance", required=True)
    parser.add_argument("--dataset", choices=sorted(DATASETS), required=True)
    args = parser.parse_args()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        values = variables(args.instance, args.dataset)
    for key, value in values.items():
        print(f"unset {key}" if value is None else f"export {key}={shlex.quote(str(value))}")

if __name__ == "__main__":
    sys.exit(main())
