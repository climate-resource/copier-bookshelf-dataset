"""Tests for the outcome job, which decides whether a candidate is ready."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from conftest import ACTION

SPEC = importlib.util.spec_from_file_location("aggregate", ACTION / "aggregate.py")
assert SPEC is not None and SPEC.loader is not None
AGGREGATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AGGREGATE)

ALL_PASSED = {"candidate": "success", "targets": "success", "record": "success"}


def target(volume: str, version: str) -> dict[str, str]:
    return {"recipe": "bookshelf.yaml", "volume": volume, "version": version}


def outcome(
    volume: str, version: str, status: str = "validated", reason: str = ""
) -> dict[str, str]:
    return {"volume": volume, "version": version, "status": status, "reason": reason}


TARGETS = [target("example", "v1"), target("example", "v2")]


def test_every_target_validated_is_ready() -> None:
    report = AGGREGATE.aggregate(
        TARGETS, [outcome("example", "v2"), outcome("example", "v1")], ALL_PASSED
    )

    assert report.ready
    assert report.rows == [
        ("example", "v1", "validated", ""),
        ("example", "v2", "validated", ""),
    ]


def test_one_failed_target_is_not_ready() -> None:
    report = AGGREGATE.aggregate(
        TARGETS,
        [outcome("example", "v1"), outcome("example", "v2", "failed", "validate")],
        {**ALL_PASSED, "record": "failure"},
    )

    assert not report.ready
    assert ("example", "v2", "failed", "validate") in report.rows
    assert "example v2: failed" in report.problems


def test_a_missing_outcome_is_not_ready() -> None:
    """A cancelled leg leaves no outcome, and that must never read as success."""
    report = AGGREGATE.aggregate(TARGETS, [outcome("example", "v1")], ALL_PASSED)

    assert not report.ready
    assert "example v2: missing" in report.problems


def test_an_unexpected_outcome_is_not_ready() -> None:
    report = AGGREGATE.aggregate(
        TARGETS,
        [outcome("example", "v1"), outcome("example", "v2"), outcome("other", "v1")],
        ALL_PASSED,
    )

    assert not report.ready
    assert ("other", "v1", "unexpected", "not in the target list") in report.rows


def test_a_duplicated_outcome_is_not_ready() -> None:
    report = AGGREGATE.aggregate(
        TARGETS,
        [outcome("example", "v1"), outcome("example", "v2"), outcome("example", "v2")],
        ALL_PASSED,
    )

    assert not report.ready
    assert "example v2: duplicated" in report.problems


def test_an_empty_target_list_is_not_ready() -> None:
    report = AGGREGATE.aggregate([], [], ALL_PASSED)

    assert not report.ready
    assert "the target list is empty" in report.problems


def test_no_target_list_is_not_ready() -> None:
    report = AGGREGATE.aggregate(None, [], {**ALL_PASSED, "targets": "failure"})

    assert not report.ready
    assert "no target list was produced" in report.problems


@pytest.mark.parametrize("result", ["skipped", "cancelled", "failure"])
def test_a_record_job_that_did_not_succeed_is_not_ready(result: str) -> None:
    """Every outcome can look validated while the job itself was cut short."""
    report = AGGREGATE.aggregate(
        TARGETS,
        [outcome("example", "v1"), outcome("example", "v2")],
        {**ALL_PASSED, "record": result},
    )

    assert not report.ready
    assert f"the record job finished as {result}" in report.problems


def test_a_merge_conflict_is_not_ready() -> None:
    report = AGGREGATE.aggregate(
        None,
        [],
        {"candidate": "failure", "targets": "skipped", "record": "skipped"},
        conflict=True,
    )

    assert not report.ready
    assert report.problems[0].startswith("merge-conflict")


def test_the_markdown_carries_the_candidate_and_a_row_per_target() -> None:
    report = AGGREGATE.aggregate(
        TARGETS, [outcome("example", "v1"), outcome("example", "v2")], ALL_PASSED
    )

    markdown = report.markdown({"head_sha": "abc", "main_sha": "def"})

    assert "- Head: `abc`" in markdown
    assert "| example | v1 | validated |  |" in markdown
    assert "Ready: every expected book was recorded and validated." in markdown


def write_json(path: Path, value: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return path


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the script the way the workflow does, on a bare interpreter."""
    return subprocess.run(
        (sys.executable, str(ACTION / "aggregate.py"), *args),
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_script_reads_each_downloaded_artifact(tmp_path: Path) -> None:
    """download-artifact puts each matched artifact in its own directory."""
    targets = write_json(tmp_path / "targets" / "targets.json", TARGETS)
    outcomes = tmp_path / "outcomes"
    for version in ("v1", "v2"):
        artifact = outcomes / f"bookshelf-bundle-example-{version}"
        write_json(artifact / "outcome.json", outcome("example", version))

    jobs = [f"--job={name}={result}" for name, result in ALL_PASSED.items()]
    result = run_script(
        "--targets", str(targets), "--outcomes-dir", str(outcomes), *jobs
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Ready" in result.stdout


def test_the_script_fails_when_nothing_was_downloaded(tmp_path: Path) -> None:
    result = run_script(
        "--targets",
        str(tmp_path / "missing.json"),
        "--outcomes-dir",
        str(tmp_path / "missing"),
        "--candidate",
        str(tmp_path / "missing.json"),
    )

    assert result.returncode == 1
    assert "no target list was produced" in result.stdout
