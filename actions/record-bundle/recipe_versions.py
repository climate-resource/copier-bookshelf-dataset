"""Resolve the versions to record, for a step that records every one of them."""

import os
import sys
from pathlib import Path

from bookshelf.publisher.recipe import load_record_recipe


def versions_to_record(recipe_file: Path, override: str) -> tuple[str, ...]:
    """Return the requested version, or every version the recipe declares."""
    if override:
        return (override,)
    return load_record_recipe(recipe_file).versions


def main() -> None:
    """Write the versions to record, in recipe order, as a step output."""
    versions = versions_to_record(Path(sys.argv[1]), os.environ.get("VERSION", ""))
    if not versions:
        sys.exit("the recipe declares no books, so there is nothing to record")

    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as stream:
        stream.write(f"versions={' '.join(versions)}\n")


if __name__ == "__main__":
    main()
