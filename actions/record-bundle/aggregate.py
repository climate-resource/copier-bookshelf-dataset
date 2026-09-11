"""Decide whether a candidate is ready: every expected book has a validated outcome.

This runs on a bare runner, so it uses nothing beyond the standard library.
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

Key = tuple[str, str]


@dataclass
class Report:
    """What the outcome job found, and whether the candidate is ready."""

    rows: list[tuple[str, str, str, str]] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        """A candidate is ready only when nothing went wrong."""
        return not self.problems

    def markdown(self, candidate: dict[str, Any] | None = None) -> str:
        """Render the report for the job summary."""
        lines = ["## Candidate outcome", ""]
        if candidate:
            lines += [
                f"- Head: `{candidate.get('head_sha', '')}`",
                f"- Main: `{candidate.get('main_sha', '')}`",
                f"- Candidate tree: `{candidate.get('candidate_tree', '')}`",
                "",
            ]
        if self.rows:
            lines += ["| Volume | Version | Status | Reason |", "|---|---|---|---|"]
            lines += [f"| {' | '.join(row)} |" for row in self.rows]
            lines.append("")
        if self.ready:
            lines.append("Ready: every expected book was recorded and validated.")
        else:
            lines.append("Not ready:")
            lines += [f"- {problem}" for problem in self.problems]
        return "\n".join(lines) + "\n"


def target_key(entry: dict[str, Any]) -> Key:
    """Identify a target, or the outcome reported for one."""
    return (str(entry.get("volume", "")), str(entry.get("version", "")))


def aggregate(
    targets: list[dict[str, Any]] | None,
    outcomes: list[dict[str, Any]],
    jobs: dict[str, str],
    conflict: bool = False,
) -> Report:
    """Compare the outcomes with the targets, and fail on anything not validated."""
    report = Report()
    if conflict:
        report.problems.append("merge-conflict: the head does not merge with main")
    report.problems += [
        f"the {job} job finished as {result}"
        for job, result in jobs.items()
        if result != "success"
    ]

    if targets is None:
        report.problems.append("no target list was produced")
    elif not targets:
        report.problems.append("the target list is empty")

    reported: dict[Key, list[dict[str, Any]]] = {}
    for outcome in outcomes:
        reported.setdefault(target_key(outcome), []).append(outcome)

    expected = [target_key(target) for target in targets or []]
    for volume, version in expected:
        found = reported.get((volume, version), [])
        if len(found) != 1:
            status = "missing" if not found else "duplicated"
            reason = f"{len(found)} outcomes reported"
        else:
            status = str(found[0].get("status", ""))
            reason = str(found[0].get("reason") or "")
        report.rows.append((volume, version, status, reason))
        if status != "validated":
            report.problems.append(f"{volume} {version}: {status}")

    for volume, version in sorted(reported.keys() - set(expected)):
        report.rows.append((volume, version, "unexpected", "not in the target list"))
        report.problems.append(f"{volume} {version} was recorded but not expected")

    return report


def read_outcomes(directory: Path) -> list[dict[str, Any]]:
    """Read the outcome at the root of each downloaded bundle artifact."""
    if not directory.is_dir():
        return []
    paths = [*directory.glob("outcome.json"), *directory.glob("*/outcome.json")]
    return [json.loads(path.read_text()) for path in sorted(paths)]


def read_json(path: Path | None) -> Any:
    """Read a JSON file that an earlier job may not have produced."""
    if path is None or not path.is_file():
        return None
    return json.loads(path.read_text())


def main() -> None:
    """Print the report as markdown, and exit non-zero unless the candidate is ready."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--outcomes-dir", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--conflict", type=lambda value: value == "true", default=False)
    parser.add_argument(
        "--job",
        action="append",
        default=[],
        metavar="NAME=RESULT",
        help="the result of a job the outcome depends on, repeated per job",
    )
    args = parser.parse_args()

    report = aggregate(
        read_json(args.targets),
        read_outcomes(args.outcomes_dir),
        dict(job.split("=", 1) for job in args.job),
        conflict=args.conflict,
    )
    print(report.markdown(read_json(args.candidate)), end="")
    sys.exit(0 if report.ready else 1)


if __name__ == "__main__":
    main()
