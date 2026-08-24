"""List the versions a recipe declares, for a step that records every one of them."""

import os
import sys
from pathlib import Path

from bookshelf.publisher.recipe import load_record_recipe


def main() -> None:
    """Write the recipe's versions, in recipe order, as a step output."""
    versions = load_record_recipe(Path(sys.argv[1])).versions
    if not versions:
        sys.exit("the recipe declares no books, so there is nothing to record")

    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as stream:
        stream.write(f"versions={' '.join(versions)}\n")


if __name__ == "__main__":
    main()
