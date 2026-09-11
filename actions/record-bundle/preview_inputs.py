"""Assemble the preview upload's inputs from the artifacts the earlier jobs left.

This runs on a bare runner in the trusted job,
so it uses nothing beyond the standard library.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def describe(target: dict[str, Any]) -> str:
    """Name a target the way the job summary reports it."""
    return f"{target.get('volume', '')} {target.get('version', '')}".strip()


def bundle_directory(artifacts: Path, target: dict[str, Any]) -> Path:
    """Where a target's bundle lands once its artifact has been downloaded."""
    volume = str(target.get("volume", ""))
    version = str(target.get("version", ""))
    return artifacts / f"bookshelf-bundle-{volume}-{version}" / version


def resolve(
    artifacts: Path, targets: list[dict[str, Any]]
) -> tuple[list[Path], list[str]]:
    """Return a bundle directory per target, and the targets that have none.

    A failed target still has a bundle, so it is uploaded and the SDK fails the preview.
    """
    bundles = []
    missing = []
    for target in targets:
        directory = bundle_directory(artifacts, target)
        if directory.is_dir():
            bundles.append(directory)
        else:
            missing.append(describe(target))
    return bundles, missing


def missing_markdown(problems: list[str]) -> str:
    """Render the reason nothing was uploaded, for the job summary."""
    lines = ["## Preview not uploaded", ""]
    lines += [f"- {problem}" for problem in problems]
    return "\n".join(lines) + "\n"


def environment_lines(candidate: dict[str, Any], bundles: list[Path]) -> str:
    """Render the candidate identity and the bundle list as `$GITHUB_ENV` lines."""
    return "".join(
        f"{name}={value}\n"
        for name, value in (
            ("HEAD_SHA", candidate.get("head_sha", "")),
            ("MAIN_SHA", candidate.get("main_sha", "")),
            ("CANDIDATE_TREE", candidate.get("candidate_tree", "")),
            ("BUNDLES", " ".join(str(bundle) for bundle in bundles)),
        )
    )


def read_json(path: Path) -> Any:
    """Read a JSON file that an earlier job may not have produced."""
    if not path.is_file():
        return None
    return json.loads(path.read_text())


def main() -> None:
    """Print the upload's environment, or report the targets that have no bundle."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    candidate = read_json(args.artifacts / "candidate.json")
    targets = read_json(args.artifacts / "targets.json")

    problems = []
    if candidate is None:
        problems.append("no candidate identity was produced")
    if targets is None:
        problems.append("no target list was produced")
    elif not targets:
        problems.append("the target list is empty")

    bundles: list[Path] = []
    if not problems:
        bundles, missing = resolve(args.artifacts, targets)
        problems += [f"{target}: no bundle was recorded" for target in missing]

    if problems:
        report = missing_markdown(problems)
        if args.summary is not None:
            with args.summary.open("a") as stream:
                stream.write(report)
        sys.exit(report)

    print(environment_lines(candidate, bundles), end="")


if __name__ == "__main__":
    main()
