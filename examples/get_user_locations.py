#!/usr/bin/env python3
"""
Example: list the locations belonging to a user.

``/geomap/api/locations`` supports filtering by an arbitrary owner via
``owners=<user_pk>`` (a choice filter over user PKs) — unlike research
projects or classification projects, whose ``owner`` filter is a boolean
tied to whoever is authenticated in the request. That means you don't need
that user's own credentials to list their locations: any account with
visibility over them can filter by ``owners=<user_pk>``.

If you only know the username, it's resolved to a pk by scanning
``/accounts/api/users`` client-side — that endpoint has no server-side
search filter, so this walks every page looking for a username match.

Usage:
    export WILDINTEL_BASE_URL="https://your-trapper-instance.example"
    export WILDINTEL_ACCESS_TOKEN="<token>"
    # or: export WILDINTEL_USER_NAME=... / WILDINTEL_USER_PASSWORD=...
    uv run python examples/get_user_locations.py <user_pk_or_username>
"""
import os
import sys

from trapper_client import TrapperClient


def resolve_user_pk(client: TrapperClient, user_pk_or_username: str) -> int:
    """Return ``user_pk_or_username`` as an int pk.

    If it isn't already numeric, resolve it by scanning
    ``/accounts/api/users`` client-side for a matching username.
    """
    if user_pk_or_username.isdigit():
        return int(user_pk_or_username)

    for user in client.users.where():
        if user.username == user_pk_or_username:
            return user.pk

    sys.exit(f"No user found with username {user_pk_or_username!r}.")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(f"Usage: {sys.argv[0]} <user_pk_or_username>")

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

    user_pk = resolve_user_pk(client, sys.argv[1])

    # owners filters by an arbitrary user pk — unlike research_projects'
    # boolean owner=True, this doesn't require authenticating as that user.
    locations = client.locations.where(owners=user_pk)

    count = 0
    for location in locations:
        count += 1
        label = location.name or location.location_id or f"location {location.pk}"
        print(f"[{location.pk}] {label} (owner: {location.owner})")

    if count == 0:
        print(f"No locations found for user pk={user_pk}.")


if __name__ == "__main__":
    main()
