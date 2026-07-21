"""Replay a bundle and report whether publishing converged on an edition."""

import argparse
import asyncio
import json
from pathlib import Path

from bookshelf_client import Bookshelf, replay
from bookshelf_client.bundle import Bundle, compute_book_bundle_hash


async def publish(root: Path, base_url: str, token: str) -> dict[str, object]:
    """Replay a bundle and return a machine readable publish outcome."""
    bundle = Bundle.read(root)
    framing = bundle.manifest.book
    if framing is None:
        raise ValueError("bundle has no book framing")

    bundle_hash = compute_book_bundle_hash(bundle.manifest)
    async with Bookshelf(base_url, token, mode="online") as client:
        existing = await client.create_draft_book(
            framing.volume,
            framing.version,
            license=framing.license,
            visibility=framing.visibility,
            bundle_hash=bundle_hash,
        )
        if existing.status == "published":
            return {
                "outcome": "no-op",
                "volume": framing.volume,
                "version": framing.version,
                "edition": existing.edition,
                "bundle_hash": bundle_hash,
                "resources": 0,
            }

        artifacts = await replay(bundle, client)
        published = await client.create_draft_book(
            framing.volume,
            framing.version,
            license=framing.license,
            visibility=framing.visibility,
            bundle_hash=bundle_hash,
        )

    return {
        "outcome": "published",
        "volume": framing.volume,
        "version": framing.version,
        "edition": published.edition,
        "bundle_hash": bundle_hash,
        "resources": len(artifacts),
    }


def main() -> None:
    """Parse arguments and print a JSON publish summary."""
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token", required=True)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(publish(args.bundle, args.base_url, args.token))))


if __name__ == "__main__":
    main()
