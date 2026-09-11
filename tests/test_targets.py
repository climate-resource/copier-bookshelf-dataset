"""Tests for the target list the CI matrix records one leg per entry of."""

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest
from conftest import ACTION

SPEC = importlib.util.spec_from_file_location("targets", ACTION / "targets.py")
assert SPEC is not None and SPEC.loader is not None
TARGETS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TARGETS)

ONE = Path("one.yaml")
TWO = Path("two.yaml")


def test_a_single_recipe_lists_every_book_in_recipe_order() -> None:
    assert TARGETS.collect_targets([(ONE, "example", ("v2", "v1"))]) == [
        {"recipe": "one.yaml", "volume": "example", "version": "v2"},
        {"recipe": "one.yaml", "volume": "example", "version": "v1"},
    ]


def test_two_recipes_list_both_volumes() -> None:
    targets = TARGETS.collect_targets(
        [(ONE, "one", ("v1",)), (TWO, "two", ("v1", "v2"))]
    )

    assert [(t["recipe"], t["volume"], t["version"]) for t in targets] == [
        ("one.yaml", "one", "v1"),
        ("two.yaml", "two", "v1"),
        ("two.yaml", "two", "v2"),
    ]


def test_a_version_narrows_the_list_to_one_book() -> None:
    assert TARGETS.collect_targets([(ONE, "example", ("v1", "v2"))], "v2") == [
        {"recipe": "one.yaml", "volume": "example", "version": "v2"}
    ]


def test_a_target_declared_twice_is_rejected() -> None:
    """Two recipes writing one book would race to publish it."""
    recipes = [(ONE, "example", ("v1", "v2")), (TWO, "example", ("v2",))]

    with pytest.raises(ValueError, match="example-v2"):
        TARGETS.collect_targets(recipes)


def test_targets_whose_artifact_names_collide_are_rejected() -> None:
    """`a-b` at `c` and `a` at `b-c` would upload the same artifact."""
    recipes = [(ONE, "a-b", ("c",)), (TWO, "a", ("b-c",))]

    with pytest.raises(ValueError, match="a-b-c"):
        TARGETS.collect_targets(recipes)


def test_an_empty_list_is_rejected() -> None:
    """A matrix over nothing would report success without recording a book."""
    with pytest.raises(ValueError, match="no books"):
        TARGETS.collect_targets([(ONE, "example", ())])


def test_a_version_no_recipe_declares_is_rejected() -> None:
    with pytest.raises(ValueError, match="no books"):
        TARGETS.collect_targets([(ONE, "example", ("v1",))], "v9")


@pytest.fixture
def sdk(monkeypatch: pytest.MonkeyPatch) -> dict[str, tuple[str, ...]]:
    """Stand in for the SDK's loader, which lives in a feedstock's environment."""
    versions: dict[str, tuple[str, ...]] = {}

    def load_record_recipe(path: Path) -> types.SimpleNamespace:
        return types.SimpleNamespace(
            volume=types.SimpleNamespace(name="example"), versions=versions[str(path)]
        )

    recipe_module = types.ModuleType("bookshelf.publisher.recipe")
    recipe_module.load_record_recipe = load_record_recipe  # type: ignore[attr-defined]
    for name in ("bookshelf", "bookshelf.publisher"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.setitem(sys.modules, "bookshelf.publisher.recipe", recipe_module)
    return versions


def test_main_writes_the_file_and_a_compact_step_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sdk: dict[str, tuple[str, ...]],
) -> None:
    """The step output feeds `fromJSON`, so it has to stay on one line."""
    sdk["bookshelf.yaml"] = ("v1", "v2")
    output = tmp_path / "github-output"
    output.write_text("earlier=kept\n")
    targets_file = tmp_path / "targets.json"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr(
        "sys.argv", ["targets.py", "--output", str(targets_file), "bookshelf.yaml"]
    )

    TARGETS.main()

    lines = output.read_text().splitlines()
    assert lines[0] == "earlier=kept"
    assert len(lines) == 2
    name, value = lines[1].split("=", 1)
    assert name == "targets"
    assert json.loads(value) == json.loads(targets_file.read_text())
    assert len(json.loads(value)) == 2


def test_main_exits_with_the_reason_on_an_empty_list(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sdk: dict[str, tuple[str, ...]],
) -> None:
    sdk["bookshelf.yaml"] = ()
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "github-output"))
    monkeypatch.setattr("sys.argv", ["targets.py", "bookshelf.yaml"])

    with pytest.raises(SystemExit, match="no books"):
        TARGETS.main()
