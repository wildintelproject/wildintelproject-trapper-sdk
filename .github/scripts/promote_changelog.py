#!/usr/bin/env python3
"""
Promote CHANGELOG.md's "Upcoming release" section to a dated, versioned entry
under "Released", and write its content (without the version heading) to a
separate notes file for use as the GitHub Release body.

Used by .github/workflows/release.yml on a tag push — no manual CHANGELOG.md
edit is required before tagging: the content of "## Upcoming release" at the
tagged commit is what gets released.
"""
from __future__ import annotations

import argparse
import sys


UPCOMING_HEADING = "## Upcoming release"
RELEASED_HEADING = "## Released"
PLACEHOLDER = "No stable release yet."


def find_section(lines: list[str], heading: str) -> tuple[int, int]:
    """Return (start, end) line indices for the section starting at `heading`.

    `start` is the index of the heading line itself; `end` is the index of
    the next top-level ("## ") heading, or len(lines) if there is none.
    """
    start = next(i for i, line in enumerate(lines) if line.rstrip("\n") == heading)
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    return start, end


def build_link(repo: str, version: str, prev_tag: str | None) -> str:
    if prev_tag:
        return f"https://github.com/{repo}/compare/{prev_tag}...v{version}"
    return f"https://github.com/{repo}/releases/tag/v{version}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--changelog", default="CHANGELOG.md")
    parser.add_argument("--version", required=True, help="e.g. 0.1.0")
    parser.add_argument("--date", required=True, help="ISO date, e.g. 2026-07-21")
    parser.add_argument("--repo", required=True, help="e.g. wildintelproject/wildintelproject-trapper-sdk")
    parser.add_argument("--prev-tag", default="", help="Previous tag (e.g. v0.1.0), empty for the first release")
    parser.add_argument("--notes-out", required=True, help="Where to write the extracted release notes")
    args = parser.parse_args()

    with open(args.changelog, encoding="utf-8") as f:
        lines = f.readlines()

    up_start, up_end = find_section(lines, UPCOMING_HEADING)
    upcoming_body = lines[up_start + 1:up_end]

    # Trim leading/trailing blank lines from the extracted body.
    while upcoming_body and upcoming_body[0].strip() == "":
        upcoming_body.pop(0)
    while upcoming_body and upcoming_body[-1].strip() == "":
        upcoming_body.pop()

    if not upcoming_body:
        print("Nothing under 'Upcoming release' — aborting promotion.", file=sys.stderr)
        sys.exit(1)

    with open(args.notes_out, "w", encoding="utf-8") as f:
        f.writelines(upcoming_body)
        f.write("\n")

    link = build_link(args.repo, args.version, args.prev_tag or None)
    new_heading = f"### [{args.version}]({link}) - {args.date}\n"

    rel_start, _ = find_section(lines, RELEASED_HEADING)
    released_rest = lines[rel_start + 1:]
    # Drop the "No stable release yet." placeholder on the first real release.
    released_rest = [
        line for line in released_rest
        if line.strip() != PLACEHOLDER
    ]
    # Trim a single leading blank line left behind by the placeholder removal.
    while released_rest and released_rest[0].strip() == "":
        released_rest.pop(0)

    new_lines = (
        lines[:up_start]
        + [UPCOMING_HEADING + "\n", "\n"]
        + lines[rel_start:rel_start + 1]
        + ["\n", new_heading, "\n"]
        + upcoming_body
        + ["\n"]
        + released_rest
    )

    with open(args.changelog, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"Promoted 'Upcoming release' to {new_heading.strip()}")


if __name__ == "__main__":
    main()
