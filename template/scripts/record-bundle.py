"""Execute the build file and record it into a reviewable bundle."""

import json
from pathlib import Path

from bookshelf.publisher import run_record

result = run_record(
    build_path=Path("build.py"),
    recipe_path=Path("bookshelf.yaml"),
    bundle_path=Path("bundle"),
)
print(json.dumps(result, sort_keys=True))
