"""Validate the structure and content hashes of a recorded bundle."""

import hashlib
import json
import sys
from pathlib import Path

from bookshelf.publisher import Bundle, compute_book_bundle_hash


def validate(root: Path) -> dict[str, object]:
    """Validate a replayable published book bundle and return its summary."""
    bundle = Bundle.read(root)
    book = bundle.manifest.book
    if book is None:
        raise ValueError("bundle has no book framing")
    if not book.published:
        raise ValueError("bundle does not record a publish operation")
    if not book.entries:
        raise ValueError("bundle has no book entries")

    resources = {
        resource.tracking_id: resource for resource in bundle.manifest.resources
    }
    for entry in book.entries:
        if entry.tracking_id not in resources:
            raise ValueError(f"book entry {entry.name_in_book!r} has no resource")

    for resource in bundle.manifest.resources:
        if resource.kind != "managed":
            continue
        data = bundle.resource_bytes(resource)
        actual = f"sha256:{hashlib.sha256(data).hexdigest()}"
        if actual != resource.hash:
            raise ValueError(
                f"resource {resource.tracking_id} has hash {resource.hash}, "
                f"got {actual}"
            )

    return {
        "bundle_path": str(root),
        "bundle_hash": compute_book_bundle_hash(bundle.manifest),
        "resources": len(bundle.manifest.resources),
        "book_entries": len(book.entries),
        "published": book.published,
    }


if __name__ == "__main__":
    print(json.dumps(validate(Path(sys.argv[1])), sort_keys=True))
