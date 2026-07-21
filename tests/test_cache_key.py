"""Tests for raw input content hash cache keys."""

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "actions" / "record-bundle" / "cache_key.py"
SPEC = importlib.util.spec_from_file_location("cache_key", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
CACHE_KEY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CACHE_KEY)


def test_declared_hashes_returns_sorted_unique_sha256_literals(tmp_path: Path) -> None:
    """Only canonical content assertions contribute to the cache key."""
    build = tmp_path / "build.py"
    build.write_text(
        'second = "sha256:' + "b" * 64 + '"\n'
        'ignored = "md5:' + "c" * 32 + '"\n'
        'first = "sha256:' + "a" * 64 + '"\n'
        "duplicate = first\n"
    )

    assert CACHE_KEY.declared_hashes(build) == [
        "sha256:" + "a" * 64,
        "sha256:" + "b" * 64,
    ]
