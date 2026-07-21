#!/usr/bin/env python3
"""
Example: import locations from a CSV file.

``/geomap/api/locations`` is read-only — Trapper's REST API has no endpoint
to create locations. ``client.locations.import_locations()`` works around
that by simulating the classic web UI's ``geomap/location/import/`` form
through cookie/session auth (``APIClientBase.session_login``) instead of the
API's token auth.

Because that login form only accepts an account email + password (not an
API token), this script needs WILDINTEL_USER_NAME (the account's *email*
address) and WILDINTEL_USER_PASSWORD — WILDINTEL_ACCESS_TOKEN alone is not
enough here, unlike every other example in this directory.

This is a best-effort workaround around an unversioned HTML form, not a
stable API integration — see the ``Warning`` section in
``LocationsComponent.import_locations``'s docstring before relying on it.

A ready-to-use sample CSV is provided at ``examples/sample_locations.csv``
(3 rows, columns matching what the server's ``LocationImporter`` requires:
``locationID``, ``longitude``, ``latitude``, plus the optional ``locationName``
and ``coordinateUncertainty``).

Note: ``research_project_pk`` and ``timezone`` are both required — the server's
import form declares them optional but (a) rejects a missing ``research_project``
in practice, and (b) persists locations via ``bulk_create()`` (which skips normal
model validation) when ``timezone`` is blank, silently creating locations with a
corrupt ``timezone`` value that later crashes *any* request that lists/serializes
them — long after the import itself reported success. See the ``import_locations``
docstring for the full explanation.

Pass ``--split`` to upload the CSV in <=512 KiB chunks instead of one request
(there's no chunked upload protocol on this endpoint — this just breaks the
CSV into several self-contained smaller CSVs), with ``--delay`` seconds
between uploads (default 1).

If a chunk is still too large/slow for the server, the upload can fail with a
network-level timeout — that's retried automatically (exponential backoff);
tune it with ``--retry-attempts`` (default 3, set to 1 to disable retrying),
``--retry-min-wait``/``--retry-max-wait`` seconds (defaults 1/10).

Usage:
    export WILDINTEL_BASE_URL="https://your-trapper-instance.example"
    export WILDINTEL_USER_NAME="you@example.com"   # must be your account's email
    export WILDINTEL_USER_PASSWORD="..."
    uv run python examples/import_locations.py examples/sample_locations.csv <research_project_pk> <timezone> \\
        [--split] [--delay SECONDS] [--retry-attempts N] [--retry-min-wait S] [--retry-max-wait S]
"""
import os
import sys

from trapper_client import TrapperClient, err


def _pop_float_flag(args: list, flag: str, default: float) -> float:
    if flag in args:
        i = args.index(flag)
        value = float(args[i + 1])
        del args[i:i + 2]
        return value
    return default


def main() -> None:
    args = sys.argv[1:]

    split = "--split" in args
    delay = _pop_float_flag(args, "--delay", 1.0)
    retry_attempts = int(_pop_float_flag(args, "--retry-attempts", 3))
    retry_min_wait = _pop_float_flag(args, "--retry-min-wait", 1.0)
    retry_max_wait = _pop_float_flag(args, "--retry-max-wait", 10.0)
    args = [a for a in args if a != "--split"]

    if len(args) != 3:
        sys.exit(
            f"Usage: {sys.argv[0]} <locations.csv> <research_project_pk> <timezone> "
            "[--split] [--delay SECONDS] [--retry-attempts N] "
            "[--retry-min-wait S] [--retry-max-wait S]"
        )

    csv_file, research_project, timezone = args

    base_url = os.environ.get("WILDINTEL_BASE_URL")
    user_name = os.environ.get("WILDINTEL_USER_NAME")
    user_password = os.environ.get("WILDINTEL_USER_PASSWORD")

    if not base_url:
        sys.exit("Set WILDINTEL_BASE_URL to your Trapper server URL.")
    if not (user_name and user_password):
        sys.exit(
            "Set WILDINTEL_USER_NAME (your account's email) and "
            "WILDINTEL_USER_PASSWORD. This import uses the web login form, "
            "not the API — an access token alone will not authenticate it."
        )

    client = TrapperClient(
        base_url=base_url,
        user_name=user_name,
        user_password=user_password,
    )

    print(f"Importing locations from {csv_file} ...")
    try:
        client.locations.import_locations(
            file=csv_file,
            research_project=research_project,
            timezone=timezone,
            split=split,
            delay=delay,
            retry_attempts=retry_attempts,
            retry_min_wait=retry_min_wait,
            retry_max_wait=retry_max_wait,
        )
    except err.APIError as e:
        sys.exit(f"Import failed: {e}")

    print("Import request accepted by the server.")


if __name__ == "__main__":
    main()
