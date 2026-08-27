"""Render every ctt.toml case from the working tree and check what comes out.

The other tests read the fixtures committed under `tests/regression/ctt`, which is one
`make ctt` behind whatever `template/` currently says. These render the working tree
directly, so an edit that only breaks at render time fails here rather than in a
generated feedstock.
"""

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml
from conftest import CASES, CTT_DIR, ENV, ROOT, shipped_files, uses_lines

pytestmark = pytest.mark.slow

# These record where the render came from: the answers file keeps the template path, and
# the workflow callers pin the commit. Rendering out of a temporary copy moves both.
RECORDS_THE_SOURCE = frozenset(
    {
        ".copier-answers.yml",
        ".github/workflows/feedstock-ci.yaml",
        ".github/workflows/feedstock-publish.yaml",
    }
)


@pytest.fixture(scope="session")
def template_source(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Copy the template out of the repository and commit it, once for every case.

    Copier renders a git checkout at its last tag, so the working tree is copied out
    to be what is under test. The copy is still committed, because the generated
    workflow callers pin themselves to the commit Copier resolves.
    """
    destination = tmp_path_factory.mktemp("template") / "src"
    destination.mkdir()
    shutil.copy(ROOT / "copier.yaml", destination / "copier.yaml")
    shutil.copytree(ROOT / "template", destination / "template")

    for command in (
        ("git", "init", "-q", "-b", "main"),
        ("git", "add", "."),
        (
            "git",
            "-c",
            "user.name=ctt",
            "-c",
            "user.email=ctt@invalid",
            "commit",
            "-qm",
            "template",
        ),
    ):
        subprocess.run(command, cwd=destination, env=ENV, check=True)

    return destination


def render(case_name: str, tmp_path: Path, source: Path) -> Path:
    """Render one answer set and return the rendered directory."""
    data_file = tmp_path / "answers.yaml"
    data_file.write_text(yaml.safe_dump(CASES[case_name]))

    destination = tmp_path / "rendered"

    result = subprocess.run(
        (
            "uv",
            "run",
            "copier",
            "copy",
            "--defaults",
            "--data-file",
            str(data_file),
            str(source),
            str(destination),
        ),
        cwd=ROOT,
        env=ENV,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"copier copy failed for {case_name}:\n{result.stdout}\n{result.stderr}"
    )
    return destination


@dataclass(frozen=True)
class Rendered:
    """One answer set, rendered from the working tree into a temporary directory."""

    name: str
    path: Path


@pytest.fixture(params=sorted(CASES), scope="module")
def rendered(
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
    template_source: Path,
) -> Rendered:
    """Render each answer set once, and run every check against that one render."""
    name = request.param
    path = render(name, tmp_path_factory.mktemp(name), template_source)
    return Rendered(name=name, path=path)


def run(command: tuple[str, ...], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a command inside a rendered feedstock, capturing what it said."""
    return subprocess.run(
        command, cwd=cwd, env=ENV, capture_output=True, text=True, check=False
    )


def test_copier_copy_needs_no_trust(rendered: Rendered) -> None:
    """The render above passed no `--trust`, so tasks would have made it fail."""
    assert (rendered.path / "bookshelf.yaml").exists()
    assert (rendered.path / "build.py").exists()
    assert (rendered.path / "renovate.json").exists()


def test_the_live_render_matches_the_committed_fixture(rendered: Rendered) -> None:
    """A stale `tests/regression/ctt` is a fixture that no longer proves anything."""
    fixture = CTT_DIR / rendered.name

    live = shipped_files(rendered.path)
    committed = shipped_files(fixture)

    assert set(live) == set(committed), "run `make ctt` and commit the result"

    differing = sorted(
        name
        for name in live
        if name not in RECORDS_THE_SOURCE and live[name] != committed[name]
    )
    assert not differing, f"run `make ctt` and commit the result: {differing}"


def ruff_pin(root: Path) -> str:
    """Return the ruff the feedstock pins, so linting matches what it ships."""
    match = re.search(r"uvx ruff@(\S+)", (root / "Makefile").read_text())
    assert match, "the rendered Makefile pins no ruff version"
    return match.group(1)


def test_the_rendered_feedstock_is_lintable(rendered: Rendered) -> None:
    """The feedstock ships a ruff config, so it has to satisfy its own config."""
    ruff = f"ruff@{ruff_pin(rendered.path)}"
    for command in (
        ("uvx", ruff, "check", "."),
        ("uvx", ruff, "format", "--check", "."),
    ):
        result = run(command, rendered.path)
        assert result.returncode == 0, (
            f"{' '.join(command)} failed:\n{result.stdout}\n{result.stderr}"
        )


def test_the_rendered_workflows_are_valid(rendered: Rendered) -> None:
    """actionlint locates a project by its git root, so the render needs one."""
    if not shutil.which("actionlint"):
        pytest.skip("actionlint is not on PATH")

    run(("git", "init", "-q", "-b", "main"), rendered.path)

    result = run(("actionlint",), rendered.path)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


def test_the_rendered_pre_commit_config_is_valid(rendered: Rendered) -> None:
    """A broken hook file only shows up when pre-commit parses it."""
    result = run(("uvx", "pre-commit", "validate-config"), rendered.path)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


def test_the_rendered_renovate_config_parses(rendered: Rendered) -> None:
    """Renovate silently ignores a config it cannot parse, so parse it here."""
    config = json.loads((rendered.path / "renovate.json").read_text())

    assert config["$schema"] == "https://docs.renovatebot.com/renovate-schema.json"
    assert config["copier"]["enabled"] is True


def test_the_rendered_callers_resolve_a_ref(rendered: Rendered) -> None:
    """An unresolved ref renders as a bare `@`, which a workflow call cannot use."""
    for name in ("feedstock-ci.yaml", "feedstock-publish.yaml"):
        calls = uses_lines(rendered.path / ".github" / "workflows" / name)

        assert calls, f"{name} calls nothing"
        for call in calls:
            assert call.rsplit("@", 1)[-1].strip(), f"{name} pinned nothing: {call}"
