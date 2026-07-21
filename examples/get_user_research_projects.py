#!/usr/bin/env python3
"""
Example: list the research projects belonging to a user.

Trapper's ``owner`` filter on ``/research/api/projects`` is a boolean tied to
whoever is authenticated in the request — there is no "owner=<user_id>"
filter. So to list a *specific* user's research projects, authenticate as
that user (their token or username/password) and filter with ``owner=True``.

Usage:
    export WILDINTEL_BASE_URL="https://your-trapper-instance.example"
    export WILDINTEL_ACCESS_TOKEN="<that user's token>"
    # or, instead of a token:
    #   export WILDINTEL_USER_NAME="..."
    #   export WILDINTEL_USER_PASSWORD="..."
    uv run python examples/get_user_research_projects.py
"""
import os
import sys

from trapper_client import TrapperClient


def main() -> None:
    base_url = os.environ.get("WILDINTEL_BASE_URL")
    access_token = os.environ.get("WILDINTEL_ACCESS_TOKEN")
    user_name = os.environ.get("WILDINTEL_USER_NAME")
    user_password = os.environ.get("WILDINTEL_USER_PASSWORD")

    if not base_url:
        sys.exit("Set WILDINTEL_BASE_URL to your Trapper server URL.")
    if not access_token and not (user_name and user_password):
        sys.exit(
            "Set WILDINTEL_ACCESS_TOKEN, or WILDINTEL_USER_NAME + "
            "WILDINTEL_USER_PASSWORD, for the user whose projects you want to list."
        )

    client = TrapperClient(
        base_url=base_url,
        access_token=access_token or None,
        user_name=user_name or None,
        user_password=user_password or None,
    )

    # owner=True asks the server for projects owned by (or with any role in)
    # the currently authenticated user. Pagination is handled transparently:
    # where() fetches pages on demand as you iterate.
    projects = client.research_projects.where(owner=True)

    count = 0
    for project in projects:
        count += 1
        label = project.acronym or project.name or f"project {project.pk}"
        print(f"[{project.pk}] {label} (owner: {project.owner})")

    if count == 0:
        print("This user has no accessible research projects.")


if __name__ == "__main__":
    main()
