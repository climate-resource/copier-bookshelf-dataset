"""Tests for the trusted preview job's input helper."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from conftest import ACTION

SPEC = importlib.util.spec_from_file_location(
    "preview_inputs", ACTION / "preview_inputs.py"
)
assert SPEC is not None and SPEC.loader is not None
PREVIEW_INPUTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREVIEW_INPUTS)

CANDIDATE = {
    "head_sha": "1111111111111111111111111111111111111111",
    "main_sha": "2222222222222222222222222222222222222222",
    "candidate_tree": "3333333333333333333333333333333333333333",
    "run_id": 42,
    "run_attempt": 1,
    "event": "pull_request",
}

TARGETS = [
    {"recipe": "bookshelf.yaml", "volume": "example", "version": "v1"},
    {"recipe": "bookshelf.yaml", "volume": "example", "version": "v2"},
]


def write_json(path: Path, value: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return path


def lay_out(
    tmp_path: Path, versions: tuple[str, ...], status: str = "validated"
) -> Path:
    """Lay the artifacts out the way the download steps leave them."""
    artifacts = tmp_path / "artifacts"
    write_json(artifacts / "candidate.json", CANDIDATE)
    write_json(artifacts / "targets.json", TARGETS)
    for version in versions:
        artifact = artifacts / f"bookshelf-bundle-example-{version}"
        write_json(
            artifact / "outcome.json",
            {"volume": "example", "version": version, "status": status, "reason": ""},
        )
        (artifact / version).mkdir(parents=True)
    return artifacts


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the script the way the workflow does, on a bare interpreter."""
    return subprocess.run(
        (sys.executable, str(ACTION / "preview_inputs.py"), *args),
        capture_output=True,
        text=True,
        check=False,
    )


def test_every_target_with_a_bundle_resolves(tmp_path: Path) -> None:
    artifacts = lay_out(tmp_path, ("v1", "v2"))

    bundles, missing = PREVIEW_INPUTS.resolve(artifacts, TARGETS)

    assert not missing
    assert bundles == [
        artifacts / "bookshelf-bundle-example-v1" / "v1",
        artifacts / "bookshelf-bundle-example-v2" / "v2",
    ]


def test_a_failed_target_is_still_uploaded(tmp_path: Path) -> None:
    """The SDK fails the preview with the bundle's reason, so it needs the bundle."""
    artifacts = lay_out(tmp_path, ("v1", "v2"), status="failed")

    bundles, missing = PREVIEW_INPUTS.resolve(artifacts, TARGETS)

    assert not missing
    assert len(bundles) == 2


def test_a_target_without_a_bundle_is_missing(tmp_path: Path) -> None:
    artifacts = lay_out(tmp_path, ("v1",))

    bundles, missing = PREVIEW_INPUTS.resolve(artifacts, TARGETS)

    assert missing == ["example v2"]
    assert len(bundles) == 1


def test_the_identity_lines_are_exact(tmp_path: Path) -> None:
    artifacts = lay_out(tmp_path, ("v1", "v2"))
    bundles, _ = PREVIEW_INPUTS.resolve(artifacts, TARGETS)

    lines = PREVIEW_INPUTS.environment_lines(CANDIDATE, bundles).splitlines()

    assert lines[:3] == [
        f"HEAD_SHA={CANDIDATE['head_sha']}",
        f"MAIN_SHA={CANDIDATE['main_sha']}",
        f"CANDIDATE_TREE={CANDIDATE['candidate_tree']}",
    ]
    assert lines[3] == f"BUNDLES={bundles[0]} {bundles[1]}"


def test_the_script_prints_the_environment(tmp_path: Path) -> None:
    artifacts = lay_out(tmp_path, ("v1", "v2"))

    result = run_script("--artifacts", str(artifacts))

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"HEAD_SHA={CANDIDATE['head_sha']}" in result.stdout
    assert "bookshelf-bundle-example-v1/v1" in result.stdout
    assert "bookshelf-bundle-example-v2/v2" in result.stdout


def test_the_script_reports_a_missing_bundle_to_the_summary(tmp_path: Path) -> None:
    """Nothing is uploaded, so the check stays at expected and still blocks merge."""
    artifacts = lay_out(tmp_path, ("v1",))
    summary = tmp_path / "summary.md"

    result = run_script("--artifacts", str(artifacts), "--summary", str(summary))

    assert result.returncode == 1
    assert "example v2: no bundle was recorded" in summary.read_text()
    assert not result.stdout


def test_the_script_reports_artifacts_that_were_never_produced(tmp_path: Path) -> None:
    result = run_script("--artifacts", str(tmp_path / "missing"))

    assert result.returncode == 1
    assert "no candidate identity was produced" in result.stderr
    assert "no target list was produced" in result.stderr


def test_the_script_reports_an_empty_target_list(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    write_json(artifacts / "candidate.json", CANDIDATE)
    write_json(artifacts / "targets.json", [])

    result = run_script("--artifacts", str(artifacts))

    assert result.returncode == 1
    assert "the target list is empty" in result.stderr
