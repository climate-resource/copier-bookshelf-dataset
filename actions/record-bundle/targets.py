"""List every (volume, version) target the recipes declare, one CI matrix leg each."""

import argparse
import json
import os
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

# A recipe file, its volume, and the versions it declares in recipe order.
Recipe = tuple[Path, str, Sequence[str]]


def collect_targets(recipes: list[Recipe], version: str = "") -> list[dict[str, str]]:
    """Return one target per book, in recipe order, narrowed to `version` when given."""
    targets = [
        {"recipe": str(path), "volume": volume, "version": book}
        for path, volume, versions in recipes
        for book in versions
        if not version or book == version
    ]

    if not targets:
        raise ValueError("the recipes declare no books, so there is nothing to record")

    # Each target uploads an artifact named `<volume>-<version>`, so it must be unique.
    names = Counter(f"{target['volume']}-{target['version']}" for target in targets)
    repeated = sorted(name for name, count in names.items() if count > 1)
    if repeated:
        raise ValueError(f"more than one target is named {', '.join(repeated)}")

    return targets


def main() -> None:
    """Write the targets to a file and, as compact JSON, to the step outputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipes", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, default=Path("targets.json"))
    parser.add_argument("--version", default="")
    args = parser.parse_args()

    # Only a feedstock's environment has the SDK, so it is imported here.
    from bookshelf.publisher.recipe import load_record_recipe  # noqa: PLC0415

    recipes = []
    for path in args.recipes:
        recipe = load_record_recipe(path)
        recipes.append((path, recipe.volume.name, recipe.versions))

    try:
        targets = collect_targets(recipes, args.version)
    except ValueError as error:
        sys.exit(str(error))

    args.output.write_text(json.dumps(targets, indent=2) + "\n")
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as stream:
        stream.write(f"targets={json.dumps(targets, separators=(',', ':'))}\n")


if __name__ == "__main__":
    main()
