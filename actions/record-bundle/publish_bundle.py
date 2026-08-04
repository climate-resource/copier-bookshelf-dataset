"""Replay a bundle and report whether publishing converged on an edition."""

import argparse
import json
from pathlib import Path

from bookshelf import Bookshelf
from bookshelf.publisher import Bundle, compute_book_bundle_hash, replay_bundle_sync


def publish(root: Path, base_url: str, token: str) -> dict[str, object]:
    """Replay a bundle and return a machine readable publish outcome."""
    bundle = Bundle.read(root)
    framing = bundle.manifest.book
    if framing is None:
        raise ValueError("bundle has no book framing")

    bundle_hash = compute_book_bundle_hash(bundle.manifest)
    with Bookshelf(base_url, auth=token) as client:
        # The bundle hash keys the draft, so a rerun resolves to the published edition.
        # Replay repeats this call,
        # so the framing sent here must match it field for field.
        drafted = client.draft_book(
            framing.volume,
            version=framing.version,
            description=framing.description,
            citation_doi=framing.citation_doi,
            license=framing.license,
            visibility=framing.visibility,
            metadata=framing.metadata,
            bundle_hash=bundle_hash,
        )
        if drafted.status == "published":
            return {
                "outcome": "no-op",
                "volume": framing.volume,
                "version": framing.version,
                "edition": drafted.metadata.edition,
                "bundle_hash": bundle_hash,
                "resources": 0,
            }

        published = replay_bundle_sync(bundle, client)

    return {
        "outcome": "published",
        "volume": framing.volume,
        "version": framing.version,
        "edition": published.metadata.edition,
        "bundle_hash": bundle_hash,
        "resources": len(bundle.manifest.resources),
    }


def main() -> None:
    """Parse arguments and print a JSON publish summary."""
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token", required=True)
    args = parser.parse_args()
    print(json.dumps(publish(args.bundle, args.base_url, args.token)))


if __name__ == "__main__":
    main()
