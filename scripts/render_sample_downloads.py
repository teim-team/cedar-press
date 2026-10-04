#!/usr/bin/env python3
"""Render each collection's sample download as the customer table, for the standalone build.

Connected, the service hands over ``repository.collection_csv``: the committed
ten-row preview passed through the vendored ``customer_sheet`` rules (owner
rulings 2026-10-04: Cedar Entity and Business IDs and each dataset's own event
IDs only; dataset and public registry identifiers kept; DUNS, Casino City and
retired Cedar schemes such as ``CEDAR-NEST-`` removed; public sources; no
version labels; one table) with a ``cite_as`` column. Standalone (no API), the
browser cannot run those rules, and until 2026-10-04 it handed over the raw
preview instead, ``CEDAR-NEST-`` IDs and all.

This writes the server's bytes, unchanged, to
``public/data/cedar/downloads/<collection>.csv`` and records each file's
SHA-256, row and column counts in ``data/cedar/sample_downloads.json``. The
standalone download (``src/features/grove/pressDownload.js``) serves only a
file whose digest matches that record, so both modes hand over the same file.
The raw previews stay where they are: the Explore reader is built on their
layout.

    python3 scripts/render_sample_downloads.py           rewrite the files
    python3 scripts/render_sample_downloads.py --check   exit 1 if any differs

Needs the server package importable (``pip install -e server``);
``server/tests/test_customer_sheet_policy.py`` runs ``--check`` in the Python
suite, which is why it is not in ``make check-generated`` (that target runs
before the Python dependencies are installed).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / "public" / "data" / "cedar" / "downloads"
RECORD = ROOT / "data" / "cedar" / "sample_downloads.json"
COMMAND = "python3 scripts/render_sample_downloads.py"


def render() -> dict[str, str]:
    """Every served collection's customer-table download, by collection id."""
    sys.path.insert(0, str(ROOT / "server"))
    from cedar_press import collections as launch
    from cedar_press import repository

    files = {}
    for dataset in launch.LAUNCH_COLLECTION:
        if launch.collection_csv(dataset.id) is None:
            continue
        text = repository.collection_csv(dataset.id)
        if text is not None:
            files[dataset.id] = text
    return files


def record(files: dict[str, str]) -> dict:
    collections = {}
    for collection, text in sorted(files.items()):
        rows = list(csv.reader(io.StringIO(text, newline="")))
        collections[collection] = {
            "path": f"/data/cedar/downloads/{collection}.csv",
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "rows": len(rows) - 1,
            "columns": len(rows[0]),
        }
    return {
        "about": "Customer-table sample downloads for the standalone build, rendered by "
        f"`{COMMAND}` from the committed previews through server/cedar_press/customer_sheet.py "
        "(the server's own bytes). Generated; do not edit.",
        "collections": collections,
    }


def expected() -> dict[Path, str]:
    files = render()
    out = {DOWNLOADS / f"{collection}.csv": text for collection, text in files.items()}
    out[RECORD] = json.dumps(record(files), indent=2) + "\n"
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="compare, do not write")
    args = parser.parse_args(argv)
    want = expected()
    stale = sorted(
        str(path.relative_to(ROOT))
        for path in {*want, *DOWNLOADS.glob("*.csv")}
        if not path.exists() or path not in want or path.read_text("utf-8") != want[path]
    )
    if args.check:
        if stale:
            print(f"Stale sample downloads: {', '.join(stale)}. Run `{COMMAND}`.")
            return 1
        print(f"Sample downloads current ({len(want) - 1} collections).")
        return 0
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    for path in DOWNLOADS.glob("*.csv"):
        if path not in want:
            path.unlink()
    for path, text in want.items():
        path.write_text(text, encoding="utf-8", newline="")
    print(f"Wrote {len(want) - 1} sample downloads and {RECORD.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
