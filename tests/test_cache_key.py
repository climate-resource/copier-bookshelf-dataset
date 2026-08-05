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

A_HASH = "sha256:" + "a" * 64
B_HASH = "sha256:" + "b" * 64


def write_build(directory: Path, source: str) -> Path:
    """Write a build file into a directory and return its path."""
    directory.mkdir(parents=True, exist_ok=True)
    build = directory / "build.py"
    build.write_text(source)
    return build


def run_main(
    build: Path, output: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, str]:
    """Run the entry point and return the outputs it wrote for the step."""
    output.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr("sys.argv", ["cache_key.py", str(build)])

    CACHE_KEY.main()

    return dict(
        line.split("=", 1) for line in output.read_text().splitlines() if "=" in line
    )


def test_declared_hashes_returns_sorted_unique_sha256_literals(tmp_path: Path) -> None:
    """Only canonical content assertions contribute to the cache key."""
    build = write_build(
        tmp_path,
        f'second = "{B_HASH}"\n'
        'ignored = "md5:' + "c" * 32 + '"\n'
        f'first = "{A_HASH}"\n'
        "duplicate = first\n",
    )

    assert CACHE_KEY.declared_hashes(build) == [A_HASH, B_HASH]


@pytest.mark.parametrize(
    ("literal", "why"),
    [
        ("sha256:" + "A" * 64, "upper case hex"),
        ("sha256:" + "a" * 63, "one digit short"),
        ("sha256:" + "a" * 65, "one digit long"),
        ("sha256:" + "g" * 64, "non hex characters"),
        ("sha256-" + "a" * 64, "the wrong separator"),
        ("a" * 64, "no algorithm prefix"),
        (" sha256:" + "a" * 64, "leading whitespace"),
        ("sha256:" + "a" * 64 + " ", "trailing whitespace"),
    ],
)
def test_declared_hashes_rejects_non_canonical_literals(
    tmp_path: Path, literal: str, why: str
) -> None:
    """A near miss must not silently become part of the key."""
    build = write_build(tmp_path, f"value = {literal!r}\n")

    assert CACHE_KEY.declared_hashes(build) == [], why


def test_declared_hashes_ignores_comments_and_composed_strings(tmp_path: Path) -> None:
    """Only a whole string literal is a declaration, so nothing else counts."""
    build = write_build(
        tmp_path,
        f"# {A_HASH}\n"
        f'joined = "sha256:" + "{"a" * 64}"\n'
        'interpolated = f"sha256:{digest}"\n',
    )

    assert CACHE_KEY.declared_hashes(build) == []


def test_declared_hashes_finds_hashes_wherever_they_are_written(
    tmp_path: Path,
) -> None:
    """A declaration is still a declaration inside a container or a signature."""
    build = write_build(
        tmp_path,
        f'inputs = {{"first": "{A_HASH}"}}\n'
        f'def fetch(expected: str = "{B_HASH}") -> None: ...\n',
    )

    assert CACHE_KEY.declared_hashes(build) == [A_HASH, B_HASH]


def test_declared_hashes_refuses_a_build_file_it_cannot_parse(tmp_path: Path) -> None:
    """A broken build file is a build failure, not an empty cache key."""
    build = write_build(tmp_path, "def broken(\n")

    with pytest.raises(SyntaxError):
        CACHE_KEY.declared_hashes(build)


def test_main_reports_a_key_derived_from_the_declared_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The key is the digest of the sorted declarations, so it is reproducible."""
    build = write_build(tmp_path, f'a = "{A_HASH}"\nb = "{B_HASH}"\n')

    outputs = run_main(build, tmp_path / "github-output", monkeypatch)

    expected = hashlib.sha256(f"{A_HASH}\n{B_HASH}".encode()).hexdigest()
    assert outputs == {"found": "true", "key": expected}


def test_main_reports_no_key_when_nothing_is_declared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without a declared input there is nothing to key a cache on."""
    build = write_build(tmp_path, "version = 'v0.1.0'\n")

    outputs = run_main(build, tmp_path / "github-output", monkeypatch)

    assert outputs == {"found": "false"}


def test_main_appends_to_an_output_file_that_already_has_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Steps share one output file, so writing it must not clobber earlier entries."""
    output = tmp_path / "github-output"
    build = write_build(tmp_path, f'a = "{A_HASH}"\n')
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr("sys.argv", ["cache_key.py", str(build)])
    output.write_text("earlier=kept\n")

    CACHE_KEY.main()

    assert output.read_text().splitlines()[0] == "earlier=kept"
    assert "found=true" in output.read_text()


def test_the_key_does_not_depend_on_declaration_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reordering the build file must not miss the cache."""
    forwards = write_build(tmp_path / "one", f'a = "{A_HASH}"\nb = "{B_HASH}"\n')
    backwards = write_build(tmp_path / "two", f'b = "{B_HASH}"\na = "{A_HASH}"\n')
    output = tmp_path / "github-output"

    assert run_main(forwards, output, monkeypatch) == run_main(
        backwards, output, monkeypatch
    )


def test_the_key_changes_when_a_declared_input_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A new upstream input has to invalidate the cached download."""
    before = write_build(tmp_path / "one", f'a = "{A_HASH}"\n')
    after = write_build(tmp_path / "two", f'a = "{B_HASH}"\n')
    output = tmp_path / "github-output"

    assert run_main(before, output, monkeypatch) != run_main(after, output, monkeypatch)


def test_the_generated_build_file_declares_exactly_its_example_input(
    feedstock: Feedstock,
) -> None:
    """The CI cache key and the build file agree about what the input is."""
    declared = CACHE_KEY.declared_hashes(feedstock.path / "build.py")

    assert declared == [feedstock.build_assignments("input_sha256")["input_sha256"]]
