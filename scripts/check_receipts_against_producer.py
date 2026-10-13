#!/usr/bin/env python3
"""Check the served release receipts against the producer's record of its releases.

``data/cedar/verified-preview-releases.json`` names, for each collection, the
Lumecon-data release the site serves: its ``release_id`` and the digest of its
consumer manifest (``manifest_sha256``). The receipts are installed by hand
during a refresh (``data/cedar/README.md``), and the repository's other checks
only prove the committed files agree with each other. This compares them with
the producer.

The producer's record is ``docs/cloud-review-inventory.json`` in a Lumecon-data
checkout: every release it built and verified in its review store, with the
manifest digest of the verified import. A receipt passes when an entry for the
same collection and ``release_id`` carries the same manifest digest.

What a pass proves, and what it does not. It proves each served release exists
on the producer's side, verified, with exactly that manifest. It does not prove
the release is the producer's newest: the inventory keeps older snapshots
beside newer ones, and it describes itself as "not the product catalog or
current publication pins". Row counts are not compared, because a release can
retain more rows than it publishes (Giving, NEED and PLOT do). The served
sample bytes are not compared, because no producer file records their digests.

    python3 scripts/check_receipts_against_producer.py --producer <Lumecon-data checkout>

CI runs it in the ``gaming-release-consumer`` job, against the pinned checkout,
before that job removes it. Exit 1 names each receipt that does not match.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPTS = ROOT / "data" / "cedar" / "verified-preview-releases.json"
INVENTORY = Path("docs") / "cloud-review-inventory.json"


def problems(receipts: dict, inventory: dict) -> list[str]:
    """One line per receipt the producer's inventory does not confirm."""
    entries: dict[tuple[str, str], list[str]] = {}
    for entry in inventory.get("collections", []):
        digest = (entry.get("aws_database_receipt") or {}).get("manifest_sha256")
        key = (entry.get("collection_id"), entry.get("release_id"))
        entries.setdefault(key, []).append(digest)
    found = []
    collections = receipts.get("collections") or {}
    if not collections:
        found.append("the receipts file lists no collections")
    for collection, receipt in sorted(collections.items()):
        digests = entries.get((collection, receipt.get("release_id")))
        if digests is None:
            found.append(
                f"{collection}: release {receipt.get('release_id')} "
                "is not in the producer's inventory"
            )
        elif receipt.get("manifest_sha256") not in digests:
            found.append(
                f"{collection}: manifest {receipt.get('manifest_sha256')} differs from the "
                f"producer's verified manifest for release {receipt.get('release_id')}"
            )
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--producer", type=Path, required=True, help="a Lumecon-data checkout")
    parser.add_argument("--receipts", type=Path, default=RECEIPTS)
    args = parser.parse_args(argv)
    receipts = json.loads(args.receipts.read_text(encoding="utf-8"))
    inventory = json.loads((args.producer / INVENTORY).read_text(encoding="utf-8"))
    found = problems(receipts, inventory)
    for line in found:
        print(line, file=sys.stderr)
    if found:
        return 1
    count = len(receipts["collections"])
    print(f"Every receipt matches a verified producer release ({count} collections)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
