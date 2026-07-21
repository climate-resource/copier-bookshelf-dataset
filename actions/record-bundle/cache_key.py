"""Derive a stable cache key from declared raw input content hashes."""

import ast
import hashlib
import os
import re
import sys
from pathlib import Path

SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


def declared_hashes(build_file: Path) -> list[str]:
    """Return unique canonical SHA256 literals declared in a build file."""
    tree = ast.parse(build_file.read_text(), filename=str(build_file))
    return sorted(
        {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and SHA256.fullmatch(node.value)
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
