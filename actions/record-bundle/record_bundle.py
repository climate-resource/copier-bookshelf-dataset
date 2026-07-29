"""Execute a standalone Jupytext build file and record it into a bundle."""

import argparse
import json
from pathlib import Path

from bookshelf.publisher import run_record


def main() -> None:
    """Parse arguments and print a JSON record summary."""
    parser = argparse.ArgumentParser()
    parser.add_argument("build", type=Path)
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()

    result = run_record(
        build_path=args.build,
        recipe_path=args.recipe,
        bundle_path=args.bundle,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
