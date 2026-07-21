#!/usr/bin/env python3
"""
Example: list the deployments at a given location.

``/geomap/api/deployments`` supports filtering by an arbitrary location pk
via ``location=<pk>`` (a choice filter over location PKs) — so, like
``locations`` (and unlike research/classification projects), you don't need
to authenticate as the location's owner to list its deployments; any
account with visibility over it works.

Usage:
    export WILDINTEL_BASE_URL="https://your-trapper-instance.example"
    export WILDINTEL_ACCESS_TOKEN="<token>"
    # or: export WILDINTEL_USER_NAME=... / WILDINTEL_USER_PASSWORD=...
    uv run python examples/get_location_deployments.py <location_pk>
"""
import os
import sys

from trapper_client import TrapperClient


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(f"Usage: {sys.argv[0]} <location_pk>")
    location_pk = sys.argv[1]

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

    # location filters by the location's pk. Pagination is handled
    # transparently: where() fetches pages on demand as you iterate.
    deployments = client.deployments.where(location=location_pk)

    count = 0
    for deployment in deployments:
        count += 1
        label = deployment.deployment_id or f"deployment {deployment.pk}"
        print(
            f"[{deployment.pk}] {label} "
            f"({deployment.start_date} → {deployment.end_date}, owner: {deployment.owner})"
        )

    if count == 0:
        print(f"No deployments found for location pk={location_pk}.")


if __name__ == "__main__":
    main()
