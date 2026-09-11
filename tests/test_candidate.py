"""Tests for the script that builds the candidate a feedstock run validates."""

import os
import subprocess
from pathlib import Path

import pytest
from conftest import ACTION
from conftest import ENV as BASE_ENV

# A developer's signing or hooks setup must not leak into these repositories.
ENV = {**BASE_ENV, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
SCRIPT = ACTION / "candidate.sh"
GIT = ("git", "-c", "user.name=t", "-c", "user.email=t@invalid")


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        (*GIT, *args), cwd=cwd, env=ENV, capture_output=True, text=True, check=True
    ).stdout.strip()


def commit(cwd: Path, name: str, content: str) -> str:
    (cwd / name).write_text(content)
    git(cwd, "add", name)
    git(cwd, "commit", "-qm", f"write {name}")
    return git(cwd, "rev-parse", "HEAD")


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    """A clone whose origin has diverged from the pull request head."""
    origin = tmp_path / "origin"
    origin.mkdir()
    git(origin, "init", "-q", "-b", "main")
    commit(origin, "base.txt", "base\n")

    work = tmp_path / "work"
    git(tmp_path, "clone", "-q", str(origin), str(work))
    return work


def run(clone: Path, tmp_path: Path, **env: str) -> tuple[int, dict[str, str]]:
    output = tmp_path / "github-output"
    output.write_text("")
    result = subprocess.run(
        ("bash", str(SCRIPT)),
        cwd=clone,
        env={**ENV, "GITHUB_OUTPUT": str(output), "MAIN_REF": "main", **env},
        capture_output=True,
        text=True,
        check=False,
    )
    outputs = dict(line.split("=", 1) for line in output.read_text().splitlines())
    return result.returncode, outputs


def test_a_pull_request_is_merged_with_the_current_main(
    clone: Path, tmp_path: Path
) -> None:
    head = commit(clone, "head.txt", "head\n")
    main = commit(tmp_path / "origin", "main.txt", "main\n")

    code, outputs = run(clone, tmp_path, EVENT="pull_request", PR_HEAD_SHA=head)

    assert code == 0
    assert outputs["conflict"] == "false"
    assert outputs["head-sha"] == head
    assert outputs["main-sha"] == main
    assert (clone / "head.txt").exists() and (clone / "main.txt").exists()
    assert outputs["candidate-tree"] == git(clone, "rev-parse", "HEAD^{tree}")


def test_a_rebuild_reproduces_the_pinned_tree(clone: Path, tmp_path: Path) -> None:
    """A later job rebuilds from the pinned main, even after main moves on."""
    head = commit(clone, "head.txt", "head\n")
    main = commit(tmp_path / "origin", "main.txt", "main\n")
    _, first = run(clone, tmp_path, EVENT="pull_request", PR_HEAD_SHA=head)
    commit(tmp_path / "origin", "later.txt", "later\n")

    code, again = run(
        clone,
        tmp_path,
        EVENT="pull_request",
        PR_HEAD_SHA=head,
        MAIN_SHA=main,
        EXPECTED_TREE=first["candidate-tree"],
    )

    assert code == 0
    assert again["candidate-tree"] == first["candidate-tree"]
    assert not (clone / "later.txt").exists()


def test_a_rebuild_that_differs_fails(clone: Path, tmp_path: Path) -> None:
    head = commit(clone, "head.txt", "head\n")

    code, _ = run(
        clone, tmp_path, EVENT="pull_request", PR_HEAD_SHA=head, EXPECTED_TREE="0" * 40
    )

    assert code == 1


def test_a_conflict_fails_and_says_so(clone: Path, tmp_path: Path) -> None:
    """A conflicted candidate must fail rather than record either side."""
    head = commit(clone, "base.txt", "head\n")
    commit(tmp_path / "origin", "base.txt", "main\n")

    code, outputs = run(clone, tmp_path, EVENT="pull_request", PR_HEAD_SHA=head)

    assert code == 1
    assert outputs == {"conflict": "true"}


def test_any_other_event_validates_the_commit_as_it_is(
    clone: Path, tmp_path: Path
) -> None:
    sha = git(clone, "rev-parse", "HEAD")

    code, outputs = run(clone, tmp_path, EVENT="push", GITHUB_SHA=sha)

    assert code == 0
    assert outputs["head-sha"] == outputs["main-sha"] == sha
    assert outputs["candidate-tree"] == git(clone, "rev-parse", "HEAD^{tree}")
