#!/usr/bin/env python3
"""
Example: import deployments from a CSV file.

``/geomap/api/deployments`` is read-only — Trapper's REST API has no
endpoint to create deployments. ``client.deployments.import_deployments()``
works around that by simulating the classic web UI's
``geomap/deployment/import/`` form through cookie/session auth
(``APIClientBase.session_login``) instead of the API's token auth.

Because that login form only accepts an account email + password (not an
API token), this script needs WILDINTEL_USER_NAME (the account's *email*
address) and WILDINTEL_USER_PASSWORD — WILDINTEL_ACCESS_TOKEN alone is not
enough here, unlike every other example in this directory.

Unlike locations, the server form requires a ``timezone`` (used to process
each deployment's start/end timestamps) — there is no default. Pass
``--create-locations`` if your CSV also provides new locations via
``locationID``/``longitude``/``latitude`` columns.

This is a best-effort workaround around an unversioned HTML form, not a
stable API integration — see the ``Warning`` section in
``DeploymentsComponent.import_deployments``'s docstring before relying on it.

A ready-to-use sample CSV is provided at ``examples/sample_deployments.csv``
(3 rows, columns matching what the server's ``DeploymentImporter`` requires:
``deploymentID``, ``locationID``, ``deploymentStart``, ``deploymentEnd``, plus
``longitude``/``latitude`` — needed here because the sample is meant to be run
with ``--create-locations`` — and the optional ``cameraModel``).

Note: ``research_project_pk`` is required — the server's import form declares
that field optional but rejects a missing value in practice (see the
``import_deployments`` docstring).

Pass ``--split`` to upload the CSV in <=512 KiB chunks instead of one request
(there's no chunked upload protocol on this endpoint — this just breaks the
CSV into several self-contained smaller CSVs), with ``--delay`` seconds
between uploads (default 1). Caution: ``--split`` together with
``--create-locations`` can create duplicate locations if the same
``locationID`` spans more than one chunk — see the ``import_deployments``
docstring.

If a chunk is still too large/slow for the server, the upload can fail with a
network-level timeout — that's retried automatically (exponential backoff);
tune it with ``--retry-attempts`` (default 3, set to 1 to disable retrying),
``--retry-min-wait``/``--retry-max-wait`` seconds (defaults 1/10).

Usage:
    export WILDINTEL_BASE_URL="https://your-trapper-instance.example"
    export WILDINTEL_USER_NAME="you@example.com"   # must be your account's email
    export WILDINTEL_USER_PASSWORD="..."
    uv run python examples/import_deployments.py examples/sample_deployments.csv \\
        Europe/Madrid <research_project_pk> --create-locations [--split] [--delay SECONDS] \\
        [--retry-attempts N] [--retry-min-wait S] [--retry-max-wait S]
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

    flags = {a for a in args if a.startswith("--")}
    positional = [a for a in args if not a.startswith("--")]

    if len(positional) != 3:
        sys.exit(
            f"Usage: {sys.argv[0]} <deployments.csv> <timezone> <research_project_pk> "
            "[--create-locations] [--update] [--split] [--delay SECONDS] "
            "[--retry-attempts N] [--retry-min-wait S] [--retry-max-wait S]"
        )

    csv_file = positional[0]
    timezone = positional[1]
    research_project = positional[2]
    create_locations = "--create-locations" in flags
    update = "--update" in flags

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

    print(f"Importing deployments from {csv_file} (timezone={timezone}) ...")
    try:
        client.deployments.import_deployments(
            file=csv_file,
            timezone=timezone,
            research_project=research_project,
            create_locations=create_locations,
            update=update,
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
