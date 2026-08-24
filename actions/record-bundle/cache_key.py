"""Derive a stable cache key from the input digests a recipe declares."""

import hashlib
import os
import re
import sys
from pathlib import Path

# The recipe is read line by line rather than parsed, because this step runs before
# `uv sync` and the runner's python has no YAML parser.
SHA256 = re.compile(r'^\s*sha256:\s*"?([0-9a-f]{64})"?\s*$')


def declared_hashes(recipe_file: Path) -> list[str]:
    """Return the unique canonical SHA256 digests a recipe declares, sorted."""
    return sorted(
        {
            match.group(1)
            for line in recipe_file.read_text().splitlines()
            if (match := SHA256.match(line))
        }
    )


def main() -> None:
    """Write cache key outputs for a GitHub Actions composite step."""
    hashes = declared_hashes(Path(sys.argv[1]))
    output = Path(os.environ["GITHUB_OUTPUT"])
    if not hashes:
        with output.open("a") as stream:
            stream.write("found=false\n")
        return

    key = hashlib.sha256("\n".join(hashes).encode()).hexdigest()
    with output.open("a") as stream:
        stream.write("found=true\n")
        stream.write(f"key={key}\n")


if __name__ == "__main__":
    main()
