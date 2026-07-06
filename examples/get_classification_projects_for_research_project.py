#!/usr/bin/env python3
"""
Example: list the classification projects linked to a given research project.

Every classification project belongs to exactly one research project (its
``research_project`` FK), and ``/media_classification/api/projects`` supports
filtering directly by that FK's pk.

Usage:
    export WILDINTEL_BASE_URL="https://your-trapper-instance.example"
    export WILDINTEL_ACCESS_TOKEN="<token>"
    # or: export WILDINTEL_USER_NAME=... / WILDINTEL_USER_PASSWORD=...
    uv run python examples/get_classification_projects_for_research_project.py <research_project_pk>
"""
import os
import sys

from trapper_client import TrapperClient


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(f"Usage: {sys.argv[0]} <research_project_pk>")
    research_project_pk = sys.argv[1]

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

    # research_project filters by the research project's pk. Pagination is
    # handled transparently: where() fetches pages on demand as you iterate.
    classification_projects = client.classification_projects.where(
        research_project=research_project_pk,
    )

    count = 0
    for project in classification_projects:
        count += 1
        print(f"[{project.pk}] {project.name} (status: {project.status}, owner: {project.owner})")

    if count == 0:
        print(f"No classification projects found for research project {research_project_pk}.")


if __name__ == "__main__":
    main()
