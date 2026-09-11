"""Tests for the target list the CI matrix records one leg per entry of."""

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest
import yaml
from conftest import ACTION


def load_record_recipe(path: Path) -> types.SimpleNamespace:
    """Read the two facts the target list needs, as the SDK's loader exposes them."""
    raw = yaml.safe_load(path.read_text())
    return types.SimpleNamespace(
        volume=types.SimpleNamespace(name=raw["volume"]["name"]),
        versions=tuple(book["version"] for book in raw.get("books") or ()),
    )


# The SDK lives in a feedstock's environment rather than this repository's.
STUB = types.ModuleType("bookshelf.publisher.recipe")
STUB.load_record_recipe = load_record_recipe  # type: ignore[attr-defined]
sys.modules.setdefault("bookshelf", types.ModuleType("bookshelf"))
sys.modules.setdefault("bookshelf.publisher", types.ModuleType("bookshelf.publisher"))
sys.modules.setdefault("bookshelf.publisher.recipe", STUB)

SPEC = importlib.util.spec_from_file_location("targets", ACTION / "targets.py")
assert SPEC is not None and SPEC.loader is not None
TARGETS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TARGETS)


def write_recipe(path: Path, volume: str, versions: list[str]) -> Path:
    """Write a recipe declaring one volume and its books."""
    path.write_text(
        yaml.safe_dump(
            {"volume": {"name": volume}, "books": [{"version": v} for v in versions]}
        )
    )
    return path


def test_a_single_recipe_lists_every_book_in_recipe_order(tmp_path: Path) -> None:
    recipe = write_recipe(tmp_path / "bookshelf.yaml", "example", ["v2", "v1"])

    assert TARGETS.collect_targets([recipe]) == [
        {"recipe": str(recipe), "volume": "example", "version": "v2"},
        {"recipe": str(recipe), "volume": "example", "version": "v1"},
    ]


def test_two_recipes_list_both_volumes(tmp_path: Path) -> None:
    first = write_recipe(tmp_path / "one.yaml", "one", ["v1"])
    second = write_recipe(tmp_path / "two.yaml", "two", ["v1", "v2"])

    targets = TARGETS.collect_targets([first, second])

    assert [(t["recipe"], t["volume"], t["version"]) for t in targets] == [
        (str(first), "one", "v1"),
        (str(second), "two", "v1"),
        (str(second), "two", "v2"),
    ]


def test_a_version_narrows_the_list_to_one_book(tmp_path: Path) -> None:
    recipe = write_recipe(tmp_path / "bookshelf.yaml", "example", ["v1", "v2"])

    assert TARGETS.collect_targets([recipe], "v2") == [
        {"recipe": str(recipe), "volume": "example", "version": "v2"}
    ]


def test_a_target_declared_twice_is_rejected(tmp_path: Path) -> None:
    """Two recipes writing one book would race to publish it."""
    first = write_recipe(tmp_path / "one.yaml", "example", ["v1", "v2"])
    second = write_recipe(tmp_path / "two.yaml", "example", ["v2"])

    with pytest.raises(ValueError, match="example v2"):
        TARGETS.collect_targets([first, second])


def test_an_empty_list_is_rejected(tmp_path: Path) -> None:
    """A matrix over nothing would report success without recording a book."""
    recipe = write_recipe(tmp_path / "bookshelf.yaml", "example", [])

    with pytest.raises(ValueError, match="no books"):
        TARGETS.collect_targets([recipe])


def test_a_version_no_recipe_declares_is_rejected(tmp_path: Path) -> None:
    recipe = write_recipe(tmp_path / "bookshelf.yaml", "example", ["v1"])

    with pytest.raises(ValueError, match="no books"):
        TARGETS.collect_targets([recipe], "v9")


def test_main_writes_the_file_and_a_compact_step_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The step output feeds `fromJSON`, so it has to stay on one line."""
    recipe = write_recipe(tmp_path / "bookshelf.yaml", "example", ["v1", "v2"])
    output = tmp_path / "github-output"
    output.write_text("earlier=kept\n")
    targets_file = tmp_path / "targets.json"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr(
        "sys.argv", ["targets.py", "--output", str(targets_file), str(recipe)]
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
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recipe = write_recipe(tmp_path / "bookshelf.yaml", "example", [])
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "github-output"))
    monkeypatch.setattr("sys.argv", ["targets.py", str(recipe)])

    with pytest.raises(SystemExit, match="no books"):
        TARGETS.main()
