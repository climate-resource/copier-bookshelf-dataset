"""Validate the recorded bundle and print its deterministic content hash."""

from pathlib import Path

from bookshelf_client.bundle import Bundle, compute_book_bundle_hash

bundle = Bundle.read(Path("bundle"))
print(compute_book_bundle_hash(bundle.manifest))
