"""Tests for `copier update` against a feedstock that already exists.

Each case tags a template version, renders a feedstock from it and commits.
It then releases a newer template version and updates the feedstock.
"""

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml
from conftest import ENV
from test_copier_questions import committed_template, copier, git

pytestmark = pytest.mark.slow


@dataclass
class Scaffold:
    """A template source repository and a feedstock rendered from its first tag."""

    source: Path
    feedstock: Path
    releases: int = 1

    def release(self, edit: Callable[[Path], None]) -> str:
        """Edit the source, commit it and tag it as the next major version."""
        edit(self.source)
        git(("add", "-A"), self.source)
        git(("commit", "-qm", "release"), self.source)
        self.releases += 1
        tag = f"v{self.releases}.0.0"
        git(("tag", tag), self.source)
        return tag

    def update(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        """Update the feedstock to the newest tag."""
        return copier("update", "--defaults", *arguments, str(self.feedstock))

    def answers(self) -> dict[str, object]:
        """Return the answers the feedstock has recorded."""
        return yaml.safe_load((self.feedstock / ".copier-answers.yml").read_text())

    def edit(self, relative: str, old: str, new: str) -> None:
        """Replace text in a feedstock file and commit it."""
        path = self.feedstock / relative
        assert old in path.read_text()
        path.write_text(path.read_text().replace(old, new))
        git(("commit", "-qam", f"edit {relative}"), self.feedstock)


@pytest.fixture
def scaffold(tmp_path: Path) -> Scaffold:
    """Render and commit a feedstock from template version v1.0.0."""
    source = committed_template(tmp_path.resolve() / "src")
    git(("tag", "v1.0.0"), source)

    feedstock = tmp_path.resolve() / "feedstock"
    created = copier(
        "copy",
        "--defaults",
        "--vcs-ref",
        "v1.0.0",
        "--data",
        "author=Grace Hopper",
        "--data",
        "author_email=grace.hopper@climate-resource.com",
        "--data",
        "dataset_name=example",
        "--data",
        "dataset_description=An update must keep the feedstock intact.",
        str(source),
        str(feedstock),
    )
    assert created.returncode == 0, f"{created.stdout}\n{created.stderr}"
    git(("init", "-q", "-b", "main"), feedstock)
    git(("add", "."), feedstock)
    git(("commit", "-qm", "scaffold"), feedstock)
    return Scaffold(source, feedstock)


def append_to(relative: str, text: str) -> Callable[[Path], None]:
    """Return an edit that appends text to a template file."""

    def edit(source: Path) -> None:
        path = source / "template" / relative
        path.write_text(path.read_text() + text)

    return edit


def assert_updated(result: subprocess.CompletedProcess[str]) -> None:
    """Fail with Copier's output unless the update succeeded."""
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


def test_an_update_applies_a_change_to_a_file_the_feedstock_never_edited(
    scaffold: Scaffold,
) -> None:
    scaffold.release(append_to("ruff.toml", "# new in v2\n"))

    assert_updated(scaffold.update())

    assert (scaffold.feedstock / "ruff.toml").read_text().endswith("# new in v2\n")
    assert not list(scaffold.feedstock.rglob("*.rej"))


def test_an_update_conflict_writes_a_rej_file_that_the_hook_rejects(
    scaffold: Scaffold,
) -> None:
    ruff = scaffold.feedstock / "ruff.toml"
    first_line = ruff.read_text().splitlines()[0]
    scaffold.edit("ruff.toml", first_line, "# the feedstock's own wording")
    scaffold.release(
        lambda source: (source / "template" / "ruff.toml").write_text(
            (source / "template" / "ruff.toml")
            .read_text()
            .replace(first_line, "# the template's new wording")
        )
    )

    assert_updated(scaffold.update("--conflict", "rej"))

    assert (scaffold.feedstock / "ruff.toml.rej").exists()
    git(("add", "-A"), scaffold.feedstock)
    hook = subprocess.run(
        ("pre-commit", "run", "forbidden-files", "--all-files"),
        cwd=scaffold.feedstock,
        env=ENV,
        capture_output=True,
        text=True,
        check=False,
    )
    assert hook.returncode != 0, hook.stdout
    assert "ruff.toml.rej" in hook.stdout


def test_an_update_adds_a_file_the_template_gained(scaffold: Scaffold) -> None:
    def add(source: Path) -> None:
        (source / "template" / "NOTICE.md").write_text("A new file.\n")

    scaffold.release(add)

    assert_updated(scaffold.update())

    assert (scaffold.feedstock / "NOTICE.md").read_text() == "A new file.\n"


def test_an_update_deletes_a_file_the_template_dropped(scaffold: Scaffold) -> None:
    """The file is removed when the feedstock never edited it."""
    assert (scaffold.feedstock / "build.py").exists()
    scaffold.release(lambda source: (source / "template" / "build.py.jinja").unlink())

    assert_updated(scaffold.update())

    assert not (scaffold.feedstock / "build.py").exists()


@pytest.mark.xfail(
    strict=True,
    reason="Copier deletes the edited file, see https://github.com/climate-resource/copier-bookshelf-dataset/issues/74",
)
def test_an_update_keeps_a_dropped_file_the_feedstock_edited(
    scaffold: Scaffold,
) -> None:
    scaffold.edit("build.py", "\n", "\n# local change\n")
    scaffold.release(lambda source: (source / "template" / "build.py.jinja").unlink())

    assert_updated(scaffold.update("--conflict", "rej"))

    assert "# local change" in (scaffold.feedstock / "build.py").read_text()
    assert not list(scaffold.feedstock.rglob("*.rej"))


def test_an_update_across_two_versions_applies_both(scaffold: Scaffold) -> None:
    scaffold.release(append_to("ruff.toml", "# new in v2\n"))
    scaffold.release(append_to("ruff.toml", "# new in v3\n"))

    assert_updated(scaffold.update())

    text = (scaffold.feedstock / "ruff.toml").read_text()
    assert "# new in v2\n# new in v3\n" in text
    assert scaffold.answers()["_commit"] == "v3.0.0"


def test_an_update_keeps_the_sdk_range_and_every_other_answer(
    scaffold: Scaffold,
) -> None:
    before = scaffold.answers()
    scaffold.release(append_to("ruff.toml", "# new in v2\n"))

    assert_updated(scaffold.update())

    assert (
        "bookshelf[publish]>=1.0,<2"
        in (scaffold.feedstock / "pyproject.toml").read_text()
    )
    after = scaffold.answers()
    assert {k: v for k, v in after.items() if k != "_commit"} == {
        k: v for k, v in before.items() if k != "_commit"
    }
