"""Replay the recorded bundle to the Bookshelf API.

Credentials are resolved by the SDK from the environment or a stored login.
"""

from pathlib import Path

from bookshelf import Bookshelf
from bookshelf.publisher import replay_bundle_sync

with Bookshelf() as client:
    book = replay_bundle_sync(Path("bundle"), client)

detail = book.metadata
print(f"{detail.series_name} {detail.version}_e{detail.edition:03} ({book.status})")
