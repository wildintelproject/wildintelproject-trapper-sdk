#!/usr/bin/env python3
"""
Example: generate and download the Camtrap DP data package of a classification project.

``/media_classification/api/package/{project_pk}/`` generates (or reuses a cached)
Camtrap DP zip package for a classification project and returns its download URL
in ``data.package``. That URL is already absolute and carries its own one-time
access token (``?rt=...``) — it does not need the client's ``Authorization``
header, so it's downloaded as-is via ``client.make_request()``.

Usage:
    export WILDINTEL_BASE_URL="https://your-trapper-instance.example"
    export WILDINTEL_ACCESS_TOKEN="<token>"
    # or: export WILDINTEL_USER_NAME=... / WILDINTEL_USER_PASSWORD=...
    uv run python examples/download_camtrapdp_for_classification_project.py <classification_project_pk> [output.zip]
"""
import os
import sys

from trapper_client import TrapperClient


def main() -> None:
    if len(sys.argv) not in (2, 3):
        sys.exit(f"Usage: {sys.argv[0]} <classification_project_pk> [output.zip]")
    project_pk = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) == 3 else f"camtrapdp_project_{project_pk}.zip"

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

    print(f"Generating (or reusing cached) Camtrap DP package for project {project_pk}...")
    response = client.classification_package.get_project_package(project_pk=project_pk)

    if response.data is None or not response.data.package:
        message = response.data.message if response.data else "No response data."
        errors = response.data.errors if response.data else None
        sys.exit(f"Could not generate the package: {message}\n{errors or ''}".rstrip())

    print(response.data.message)
    print(f"Downloading from {response.data.package} ...")

    file_response = client.make_request(endpoint=response.data.package, method="GET")
    with open(output_path, "wb") as f:
        f.write(file_response.content)

    print(f"Saved to {output_path}")


if __name__ == "__main__":
    main()
