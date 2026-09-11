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

TARGETS = [
    {"recipe": "bookshelf.yaml", "volume": "example", "version": "v1"},
    {"recipe": "bookshelf.yaml", "volume": "example", "version": "v2"},
]


def write_json(path: Path, value: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return path


def lay_out(
    tmp_path: Path,
    versions: tuple[str, ...],
    status: str = "validated",
    reason: str = "",
) -> Path:
    """Lay the artifacts out the way the download steps leave them."""
    artifacts = tmp_path / "artifacts"
    write_json(artifacts / "targets.json", TARGETS)
    for version in versions:
        artifact = artifacts / f"bookshelf-bundle-example-{version}"
        write_json(
            artifact / "outcome.json",
            {
                "volume": "example",
                "version": version,
                "status": status,
                "reason": reason,
            },
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

    bundles, problems = PREVIEW_INPUTS.resolve(artifacts, TARGETS)

    assert not problems
    assert bundles == [
        artifacts / "bookshelf-bundle-example-v1" / "v1",
        artifacts / "bookshelf-bundle-example-v2" / "v2",
    ]


def test_a_failed_target_is_still_uploaded(tmp_path: Path) -> None:
    """The SDK fails the preview with the bundle's reason, so it needs the bundle."""
    artifacts = lay_out(tmp_path, ("v1", "v2"), status="failed")

    bundles, problems = PREVIEW_INPUTS.resolve(artifacts, TARGETS)

    assert not problems
    assert len(bundles) == 2


def test_a_target_without_an_artifact_has_no_bundle(tmp_path: Path) -> None:
    artifacts = lay_out(tmp_path, ("v1",))

    bundles, problems = PREVIEW_INPUTS.resolve(artifacts, TARGETS)

    assert problems == ["example v2: no bundle was recorded"]
    assert len(bundles) == 1


def test_a_record_that_died_early_reports_its_reason(tmp_path: Path) -> None:
    """The record job writes an outcome even when it never lays a bundle out."""
    artifacts = lay_out(tmp_path, ("v1",))
    write_json(
        artifacts / "bookshelf-bundle-example-v2" / "outcome.json",
        {"volume": "example", "version": "v2", "status": "failed", "reason": "boom"},
    )

    _, problems = PREVIEW_INPUTS.resolve(artifacts, TARGETS)

    assert problems == ["example v2: no bundle was recorded (boom)"]


def test_the_script_prints_the_bundles(tmp_path: Path) -> None:
    artifacts = lay_out(tmp_path, ("v1", "v2"))

    result = run_script("--artifacts", str(artifacts))

    assert result.returncode == 0, result.stdout + result.stderr
    first = artifacts / "bookshelf-bundle-example-v1" / "v1"
    second = artifacts / "bookshelf-bundle-example-v2" / "v2"
    assert result.stdout == f"BUNDLES={first} {second}\n"


def test_the_script_reports_a_missing_bundle_to_the_summary(tmp_path: Path) -> None:
    """Nothing is uploaded, so the check stays at expected and still blocks merge."""
    artifacts = lay_out(tmp_path, ("v1",))
    summary = tmp_path / "summary.md"

    result = run_script("--artifacts", str(artifacts), "--summary", str(summary))

    assert result.returncode == 1
    assert "example v2: no bundle was recorded" in summary.read_text()
    assert not result.stdout


def test_the_script_reports_a_target_list_that_was_never_produced(
    tmp_path: Path,
) -> None:
    result = run_script("--artifacts", str(tmp_path / "missing"))

    assert result.returncode == 1
    assert "no target list was produced" in result.stderr


def test_the_script_reports_an_empty_target_list(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    write_json(artifacts / "targets.json", [])

    result = run_script("--artifacts", str(artifacts))

    assert result.returncode == 1
    assert "the target list is empty or not a list" in result.stderr


def test_the_script_refuses_a_target_that_could_inject_environment(
    tmp_path: Path,
) -> None:
    """Pull request code writes the target list, so it must not reach `$GITHUB_ENV`."""
    artifacts = lay_out(tmp_path, ("v1", "v2"))
    forged = {
        "recipe": "bookshelf.yaml",
        "volume": "example",
        "version": "v3\nBASH_ENV=x",
    }
    write_json(artifacts / "targets.json", [*TARGETS, forged])

    result = run_script("--artifacts", str(artifacts))

    assert result.returncode == 1
    assert "unsafe volume or version" in result.stderr
    assert not result.stdout


def test_the_script_refuses_a_target_that_walks_out_of_its_artifact(
    tmp_path: Path,
) -> None:
    artifacts = lay_out(tmp_path, ("v1", "v2"))
    write_json(
        artifacts / "targets.json",
        [*TARGETS, {"recipe": "bookshelf.yaml", "volume": "example", "version": ".."}],
    )

    result = run_script("--artifacts", str(artifacts))

    assert result.returncode == 1
    assert "unsafe volume or version" in result.stderr
