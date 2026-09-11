"""List the bundles the preview upload sends, from the artifacts the earlier jobs left.

This runs on a bare runner in the trusted job,
so it uses nothing beyond the standard library.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# The target list comes from pull request code and names paths bound for `$GITHUB_ENV`.
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def describe(target: dict[str, Any]) -> str:
    """Name a target the way the job summary reports it."""
    return f"{target.get('volume', '')} {target.get('version', '')}".strip()


def artifact_directory(artifacts: Path, target: dict[str, Any]) -> Path:
    """Where a target's artifact lands once a pattern download has fetched it."""
    return artifacts / f"bookshelf-bundle-{target['volume']}-{target['version']}"


def unsafe_targets(targets: list[Any]) -> list[str]:
    """Name the targets that are not an object with a plain volume and version."""
    return [
        f"target {json.dumps(target)} has an unsafe volume or version"
        for target in targets
        if not isinstance(target, dict)
        or not all(
            NAME.fullmatch(str(target.get(key, ""))) for key in ("volume", "version")
        )
    ]


def no_bundle_reason(artifact: Path) -> str:
    """Explain a missing bundle with the reason its record job reported, if any."""
    outcome = read_json(artifact / "outcome.json")
    if isinstance(outcome, dict) and outcome.get("reason"):
        return f"no bundle was recorded ({outcome['reason']})"
    return "no bundle was recorded"


def resolve(
    artifacts: Path, targets: list[dict[str, Any]]
) -> tuple[list[Path], list[str]]:
    """Return a bundle directory per target, and a problem per target without one.

    A failed target still has a bundle, so it is uploaded and the SDK fails the preview.
    """
    bundles = []
    problems = []
    for target in targets:
        artifact = artifact_directory(artifacts, target)
        bundle = artifact / str(target["version"])
        if bundle.is_dir():
            bundles.append(bundle)
        else:
            problems.append(f"{describe(target)}: {no_bundle_reason(artifact)}")
    return bundles, problems


def not_uploaded_markdown(problems: list[str]) -> str:
    """Render the reason nothing was uploaded, for the job summary."""
    lines = ["## Preview not uploaded", ""]
    lines += [f"- {problem}" for problem in problems]
    return "\n".join(lines) + "\n"


def read_json(path: Path) -> Any:
    """Read a JSON file that an earlier job may not have produced."""
    if not path.is_file():
        return None
    return json.loads(path.read_text())


def main() -> None:
    """Print the `BUNDLES` line for `$GITHUB_ENV`, or report why nothing is uploaded."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    targets = read_json(args.artifacts / "targets.json")
    if targets is None:
        problems = ["no target list was produced"]
    elif not isinstance(targets, list) or not targets:
        problems = ["the target list is empty or not a list"]
    else:
        problems = unsafe_targets(targets)

    bundles: list[Path] = []
    if not problems:
        bundles, problems = resolve(args.artifacts, targets)

    if problems:
        report = not_uploaded_markdown(problems)
        if args.summary is not None:
            with args.summary.open("a") as stream:
                stream.write(report)
        sys.exit(report)

    print(f"BUNDLES={' '.join(str(bundle) for bundle in bundles)}")


if __name__ == "__main__":
    main()
