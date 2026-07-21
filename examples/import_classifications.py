#!/usr/bin/env python3
"""
Example: import expert/AI observations into a classification project.

Unlike ``import_locations.py``/``import_deployments.py``, this does **not**
create new records: ``client.classification_results.import_classifications()``
posts to a real, token-authenticated REST endpoint
(``media_classification/api/classifications/import/``) that *re-applies*
expert/AI classification data (species, count, approval, ...) to
**already-existing** ``Classification`` rows in a project, matched by their
internal ``_id`` (their primary key). The server rejects any ``_id`` that
doesn't already exist in that project (a "whitelist" check) — a CSV with
made-up IDs will always fail.

Because of that, this script has two modes:

1. ``--fetch N``: writes N *real* existing observation rows from your own
   classification project to ``<csv_file>``, in the exact format the import
   expects (``_id``, ``observationType``, ``scientificName``, ``count``,
   ``classificationMethod``). Since this re-exports data that's already on
   the server, re-importing it as-is is a safe round-trip to test the whole
   code path — edit a value first (e.g. ``scientificName``) if you want to
   verify the import actually changes something.
2. Default (no ``--fetch``): imports ``<csv_file>`` into the given project.

A static *template* is provided at ``examples/sample_observations.csv`` — its
``_id`` values (1, 2) are placeholders and almost certainly don't exist in
your project. Use ``--fetch`` to get a CSV that will actually work against
your server, rather than editing that template's IDs by hand.

Pass ``--split`` to upload the CSV in <=512 KiB chunks instead of one request
(there's no chunked upload protocol on this endpoint — this just breaks the
CSV into several self-contained smaller CSVs), with ``--delay`` seconds
between uploads (default 1). Unlike ``import_locations.py``/
``import_deployments.py``, this endpoint is a real REST API that normally
takes a full file in one request — only use ``--split`` if a large CSV hits
a request-size limit or times out.

If a chunk is still too large/slow for the server, the upload can fail with a
network-level timeout — that's retried automatically (exponential backoff);
tune it with ``--retry-attempts`` (default 3, set to 1 to disable retrying),
``--retry-min-wait``/``--retry-max-wait`` seconds (defaults 1/10).

Usage:
    export WILDINTEL_BASE_URL="https://your-trapper-instance.example"
    export WILDINTEL_ACCESS_TOKEN="<token>"
    # or: export WILDINTEL_USER_NAME=... / WILDINTEL_USER_PASSWORD=...

    # Step 1: get a real, importable CSV from your own project (5 rows here)
    uv run python examples/import_classifications.py <project_id> real_observations.csv --fetch 5

    # Step 2: import it back (optionally edit a value first to see it take effect)
    uv run python examples/import_classifications.py <project_id> real_observations.csv \\
        [--split] [--delay SECONDS] [--retry-attempts N] [--retry-min-wait S] [--retry-max-wait S]
"""
import csv
import os
import sys

from trapper_client import TrapperClient, err

FETCH_COLUMNS = ["_id", "observationType", "scientificName", "count", "classificationMethod"]


def _pop_float_flag(args: list, flag: str, default: float) -> float:
    if flag in args:
        i = args.index(flag)
        value = float(args[i + 1])
        del args[i:i + 2]
        return value
    return default


def fetch_sample(client: TrapperClient, project_id: str, csv_file: str, n: int) -> None:
    """Write N real, currently-existing observation rows for a project to csv_file."""
    page = client.classification_results.get_project_results(
        project_pk=project_id, page=1, page_size=n, camtrapdp=False,
    )
    if not page.results:
        sys.exit(f"No observations found for project {project_id} — nothing to fetch.")

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FETCH_COLUMNS)
        writer.writeheader()
        for row in page.results:
            data = row.model_dump(by_alias=True, mode="json")
            writer.writerow({col: data.get(col, "") for col in FETCH_COLUMNS})

    print(f"Wrote {len(page.results)} real observation row(s) from project {project_id} to {csv_file}.")
    print("These re-apply the SAME data already on the server — safe to import as-is for a test.")


def main() -> None:
    args = sys.argv[1:]

    fetch_n = None
    if "--fetch" in args:
        i = args.index("--fetch")
        try:
            fetch_n = int(args[i + 1])
        except (IndexError, ValueError):
            sys.exit("--fetch requires a number, e.g. --fetch 5")
        del args[i:i + 2]

    split = "--split" in args
    delay = _pop_float_flag(args, "--delay", 1.0)
    retry_attempts = int(_pop_float_flag(args, "--retry-attempts", 3))
    retry_min_wait = _pop_float_flag(args, "--retry-min-wait", 1.0)
    retry_max_wait = _pop_float_flag(args, "--retry-max-wait", 10.0)
    args = [a for a in args if a != "--split"]

    if len(args) != 2:
        sys.exit(
            f"Usage: {sys.argv[0]} <project_id> <observations.csv> "
            "[--fetch N] [--split] [--delay SECONDS] "
            "[--retry-attempts N] [--retry-min-wait S] [--retry-max-wait S]"
        )

    project_id, csv_file = args

    base_url = os.environ.get("WILDINTEL_BASE_URL")
    access_token = os.environ.get("WILDINTEL_ACCESS_TOKEN")
    user_name = os.environ.get("WILDINTEL_USER_NAME")
    user_password = os.environ.get("WILDINTEL_USER_PASSWORD")

    if not base_url:
        sys.exit("Set WILDINTEL_BASE_URL to your Trapper server URL.")
    if not access_token and not (user_name and user_password):
        sys.exit(
            "Set WILDINTEL_ACCESS_TOKEN, or WILDINTEL_USER_NAME + "
            "WILDINTEL_USER_PASSWORD."
        )

    client = TrapperClient(
        base_url=base_url,
        access_token=access_token or None,
        user_name=user_name or None,
        user_password=user_password or None,
    )

    if fetch_n is not None:
        fetch_sample(client, project_id, csv_file, fetch_n)
        return

    print(f"Importing observations from {csv_file} into project {project_id} ...")
    try:
        result = client.classification_results.import_classifications(
            project_id=project_id,
            file=csv_file,
            split=split,
            delay=delay,
            retry_attempts=retry_attempts,
            retry_min_wait=retry_min_wait,
            retry_max_wait=retry_max_wait,
        )
    except err.APIError as e:
        sys.exit(f"Import failed: {e}")

    results = result if isinstance(result, list) else [result]
    for i, r in enumerate(results, start=1):
        prefix = f"[chunk {i}/{len(results)}] " if split else ""
        print(f"{prefix}{r.data.message}")
        if r.data.task_id:
            print(f"{prefix}Task ID: {r.data.task_id}")


if __name__ == "__main__":
    main()
