"""
Extract the changes from the latest version in our CHANGELOG

These can then be used in our release template.
"""

from pathlib import Path

CHANGELOG = Path("CHANGELOG.md")
PACKAGE_NAME = "{{dataset_name}}"


def main() -> None:
    """
    Extract the latest version changes from our CHANGELOG

    They are printed to stdout
    """
    with open(CHANGELOG) as fh:
        changelog_raw = fh.read()

    check_for_next_version = False
    grab_notes = False
    latest_version_notes: list[str] = []
    for line in changelog_raw.splitlines():
        if not check_for_next_version:
            if line == "<!-- towncrier release notes start -->":
                check_for_next_version = True

            continue

        if not grab_notes:
            if line.startswith(f"## {PACKAGE_NAME}"):
                grab_notes = True

            continue

        # We are grabbing notes now
        # If we've reached the next version's notes, break
        if line.startswith(f"## {PACKAGE_NAME}"):
            break

        latest_version_notes.append(line)

    print("\n".join(latest_version_notes))


if __name__ == "__main__":
    main()
