"""Tests for raw input content hash cache keys."""

import hashlib
import importlib.util
from pathlib import Path

import pytest
from conftest import Feedstock

MODULE_PATH = Path(__file__).parents[1] / "actions" / "record-bundle" / "cache_key.py"
SPEC = importlib.util.spec_from_file_location("cache_key", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
CACHE_KEY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CACHE_KEY)

A_HASH = "a" * 64
B_HASH = "b" * 64


def write_recipe(directory: Path, source: str) -> Path:
    """Write a recipe into a directory and return its path."""
    directory.mkdir(parents=True, exist_ok=True)
    recipe = directory / "bookshelf.yaml"
    recipe.write_text(source)
    return recipe


def run_main(
    recipe: Path, output: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, str]:
    """Run the entry point and return the outputs it wrote for the step."""
    output.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr("sys.argv", ["cache_key.py", str(recipe)])

    CACHE_KEY.main()

    return dict(
        line.split("=", 1) for line in output.read_text().splitlines() if "=" in line
    )


def test_declared_hashes_returns_sorted_unique_digests(tmp_path: Path) -> None:
    """Only the digests a recipe declares contribute to the cache key."""
    recipe = write_recipe(
        tmp_path,
        "books:\n"
        "  - version: '2'\n"
        "    resources:\n"
        f"      raw:\n        sha256: {B_HASH}\n"
        "  - version: '1'\n"
        "    resources:\n"
        f'      raw:\n        sha256: "{A_HASH}"\n'
        f"      same:\n        sha256: {B_HASH}\n",
    )

    assert CACHE_KEY.declared_hashes(recipe) == [A_HASH, B_HASH]


@pytest.mark.parametrize(
    ("line", "why"),
    [
        (f"    sha256: {'A' * 64}", "upper case hex"),
        (f"    sha256: {'a' * 63}", "one digit short"),
        (f"    sha256: {'a' * 65}", "one digit long"),
        (f"    sha256: {'g' * 64}", "non hex characters"),
        (f"    md5: {'a' * 64}", "another algorithm"),
        (f"    # sha256: {'a' * 64}", "a commented out digest"),
        (f"    uri: https://example.invalid/{'a' * 64}", "a digest inside a url"),
    ],
)
def test_declared_hashes_rejects_non_canonical_declarations(
    tmp_path: Path, line: str, why: str
) -> None:
    """A near miss must not silently become part of the key."""
    recipe = write_recipe(tmp_path, f"{line}\n")

    assert CACHE_KEY.declared_hashes(recipe) == [], why


def test_main_reports_a_key_derived_from_the_declared_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The key is the digest of the sorted declarations, so it is reproducible."""
    recipe = write_recipe(tmp_path, f"  sha256: {A_HASH}\n  sha256: {B_HASH}\n")

    outputs = run_main(recipe, tmp_path / "github-output", monkeypatch)

    expected = hashlib.sha256(f"{A_HASH}\n{B_HASH}".encode()).hexdigest()
    assert outputs == {"found": "true", "key": expected}


def test_main_reports_no_key_when_nothing_is_declared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A checked-in input is hashed by the recorder, so there is nothing to key on."""
    recipe = write_recipe(tmp_path, "books:\n  - version: 'v0.1.0'\n")

    outputs = run_main(recipe, tmp_path / "github-output", monkeypatch)

    assert outputs == {"found": "false"}


def test_main_appends_to_an_output_file_that_already_has_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Steps share one output file, so writing it must not clobber earlier entries."""
    output = tmp_path / "github-output"
    recipe = write_recipe(tmp_path, f"  sha256: {A_HASH}\n")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr("sys.argv", ["cache_key.py", str(recipe)])
    output.write_text("earlier=kept\n")

    CACHE_KEY.main()

    assert output.read_text().splitlines()[0] == "earlier=kept"
    assert "found=true" in output.read_text()


def test_the_key_does_not_depend_on_declaration_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reordering the recipe must not miss the cache."""
    forwards = write_recipe(
        tmp_path / "one", f"  sha256: {A_HASH}\n  sha256: {B_HASH}\n"
    )
    backwards = write_recipe(
        tmp_path / "two", f"  sha256: {B_HASH}\n  sha256: {A_HASH}\n"
    )
    output = tmp_path / "github-output"

    assert run_main(forwards, output, monkeypatch) == run_main(
        backwards, output, monkeypatch
    )


def test_the_key_changes_when_a_declared_input_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A new upstream input has to invalidate the cached download."""
    before = write_recipe(tmp_path / "one", f"  sha256: {A_HASH}\n")
    after = write_recipe(tmp_path / "two", f"  sha256: {B_HASH}\n")
    output = tmp_path / "github-output"

    assert run_main(before, output, monkeypatch) != run_main(after, output, monkeypatch)


def test_the_generated_recipe_declares_no_digest_to_cache(
    feedstock: Feedstock,
) -> None:
    """The scaffold reads a checked-in input, which is never fetched or cached."""
    assert CACHE_KEY.declared_hashes(feedstock.path / "bookshelf.yaml") == []
